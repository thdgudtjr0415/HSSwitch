"""
HSSwitch — 스피커/헤드셋/마이크 빠른 전환 프로그램

- 메인 창: 개별 전환 / 프로필 / 장치 별칭 / 설정 탭 (다크모드는 트레이 팝업에만 적용)
- 트레이 아이콘 좌클릭: pywebview 팝업(tray_popup_web.py)으로 프로필/장치 빠른 전환
- 트레이 아이콘 우클릭: 열기/종료
- 전환 시 Console/Multimedia/Communications 세 역할 모두 갱신
"""

import ctypes
import os
import sys
import threading
import time
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import comtypes
import keyboard
import pystray
from PIL import ImageTk

import audio_devices
import config_manager
import icon_art
import icon_store
import startup_manager
import tray_popup_web
import updater
from policy_config import set_default_device
from version import APP_VERSION

APP_TITLE = "HSSwitch"


def _resource_path(relative_path: str) -> str:
    """소스 실행과 PyInstaller 빌드(번들 파일은 sys._MEIPASS 아래) 양쪽에서 데이터 파일 경로를 찾는다."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


ICON_ICO_PATH = _resource_path(os.path.join("assets", "icon.ico"))

_SINGLE_INSTANCE_MUTEX_NAME = "Global\\HSSwitchSingleInstanceMutex"
_instance_mutex_handle = None  # 프로세스가 끝날 때까지 들고 있어야 뮤텍스가 유지된다


def _ensure_single_instance() -> bool:
    """이미 실행 중이면 그 창을 앞으로 가져오고 False를 반환한다(트레이 아이콘이 여러 개 뜨는 것 방지)."""
    global _instance_mutex_handle
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, _SINGLE_INSTANCE_MUTEX_NAME)
    already_running = ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
    if already_running:
        hwnd = ctypes.windll.user32.FindWindowW(None, APP_TITLE)
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        return False
    _instance_mutex_handle = mutex
    return True


def switch_device(playback_id: str | None, recording_id: str | None) -> list[str]:
    """재생/녹음을 따로 전환한다. 한쪽이 실패해도 다른 쪽은 계속하고, 실패한 항목("재생"/"녹음")을 돌려준다."""
    failed = []
    for kind, device_id in (("재생", playback_id), ("녹음", recording_id)):
        if not device_id:
            continue
        try:
            set_default_device(device_id)
        except Exception:
            failed.append(kind)
    return failed


class HSSwitchApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self._center_window(self.root, 640, 500)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        try:
            # default=True: 이 root에서 파생되는 Toplevel(프로필 편집 창 등)에도 같은 아이콘이 적용된다
            self.root.iconbitmap(default=ICON_ICO_PATH)
        except Exception:
            pass  # 아이콘을 못 찾아도 실행은 막지 않는다

        try:
            ttk.Style(self.root).theme_use("vista")
        except tk.TclError:
            pass  # Windows 전용 테마. 없으면 기본 테마 사용

        self.playback_devices: list[audio_devices.DeviceInfo] = []
        self.recording_devices: list[audio_devices.DeviceInfo] = []
        self.profiles: list[dict] = config_manager.load_profiles()
        # refresh_devices()가 트레이 갱신을 부르므로, 트레이가 만들어지기 전에도 속성은 있어야 한다
        self.tray_icon = None
        self._tray_key = None

        # 다른 스레드에서 tkinter 위젯을 직접 호출하면 안 되므로 미리 캐싱
        self.screen_width = root.winfo_screenwidth()
        self.screen_height = root.winfo_screenheight()

        self._build_ui()
        self.refresh_devices()
        self._register_hotkeys()

        self._start_tray_thread()

        # 부팅 직후에는 오디오 장치(특히 무선 헤드셋)가 아직 안 잡혀 목록이 비어 있을 수 있어 다시 조회한다
        if "--startup" in sys.argv:
            self.root.after(4000, self._retry_refresh_devices_if_empty)
            self.root.after(10000, self._retry_refresh_devices_if_empty)

        # 창이 뜨는 타이밍과 겹치지 않게 늦춰서 확인한다. 꺼져 있어도 수동 "업데이트 확인"은 항상 동작한다.
        if config_manager.load_auto_update_check():
            self.root.after(2000, lambda: self._check_for_update(silent=True))

    def _retry_refresh_devices_if_empty(self):
        if not self.playback_devices and not self.recording_devices:
            self.refresh_devices()

    def switch_device(self, playback_id, recording_id) -> list[str]:
        failed = switch_device(playback_id, recording_id)
        if failed:
            # 팝업/단축키로 전환하면 메인 창이 숨겨져 있어 상태바가 안 보이므로 트레이 알림도 보낸다
            message = f"{'/'.join(failed)} 장치를 바꾸지 못했어요. 장치가 켜져 있고 연결돼 있는지 확인해 주세요."
            self.status_var.set(message)
            self._notify(message)
        else:
            name = ""
            if playback_id:
                name = self._name_for(self.playback_devices, playback_id)
            if recording_id:
                name = self._name_for(self.recording_devices, recording_id)
            self.status_var.set(f"전환됨: {name}")
        self._refresh_profile_tree()
        return failed

    def _notify(self, message: str):
        try:
            if self.tray_icon:
                self.tray_icon.notify(message, APP_TITLE)
        except Exception:
            pass  # 알림 실패가 전환 동작을 막으면 안 된다

    def _name_for(self, devices, device_id):
        for d in devices:
            if d.id == device_id:
                return config_manager.get_display_name(d.id, d.name)
        return device_id

    # ---------- 설정(테마) ----------
    def _build_settings_tab(self, parent):
        ttk.Label(parent, text="테마", font=("", 10, "bold")).pack(anchor="w", padx=10, pady=(14, 6))
        ttk.Label(
            parent, text="트레이 팝업에만 적용돼요.", foreground="gray"
        ).pack(anchor="w", padx=10, pady=(0, 6))

        self.theme_var = tk.StringVar(value=config_manager.load_theme())
        for value, label in (
            ("system", "시스템 설정 따르기"),
            ("light", "라이트 모드"),
            ("dark", "다크 모드"),
        ):
            ttk.Radiobutton(
                parent, text=label, value=value, variable=self.theme_var,
                command=self._on_theme_change,
            ).pack(anchor="w", padx=16, pady=2)

        ttk.Label(parent, text="시작", font=("", 10, "bold")).pack(anchor="w", padx=10, pady=(20, 6))
        self.startup_var = tk.BooleanVar(value=startup_manager.is_startup_enabled())
        ttk.Checkbutton(
            parent, text="Windows 부팅 시 자동 실행", variable=self.startup_var,
            command=self._on_startup_toggle,
        ).pack(anchor="w", padx=16, pady=2)

        self._build_update_row(parent)

    def _on_startup_toggle(self):
        startup_manager.set_startup_enabled(self.startup_var.get())

    def _on_theme_change(self):
        config_manager.set_theme(self.theme_var.get())

    # ---------- 업데이트 ----------
    def _build_update_row(self, parent):
        ttk.Label(parent, text="업데이트", font=("", 10, "bold")).pack(anchor="w", padx=10, pady=(20, 6))

        self.auto_update_var = tk.BooleanVar(value=config_manager.load_auto_update_check())
        ttk.Checkbutton(
            parent, text="시작할 때 자동으로 업데이트 확인", variable=self.auto_update_var,
            command=self._on_auto_update_toggle,
        ).pack(anchor="w", padx=16, pady=2)
        ttk.Label(
            parent,
            text="꺼두면 새 버전이 나와도 알림이 안 떠요. \"업데이트 확인\" 버튼으로는 언제든 직접 확인할 수 있어요.",
            wraplength=480, foreground="gray",
        ).pack(anchor="w", padx=16, pady=(0, 6))

        row = ttk.Frame(parent)
        row.pack(anchor="w", padx=16, pady=2, fill="x")
        ttk.Label(row, text=f"현재 버전: {APP_VERSION}").pack(side="left")
        ttk.Button(
            row, text="업데이트 확인", command=lambda: self._check_for_update(silent=False)
        ).pack(side="left", padx=(10, 0))

    def _on_auto_update_toggle(self):
        config_manager.set_auto_update_check(self.auto_update_var.get())

    def _check_for_update(self, silent: bool):
        def worker():
            manifest = updater.check_for_update()
            self.root.after(0, lambda: self._on_update_check_result(manifest, silent))

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_check_result(self, manifest, silent: bool):
        if manifest:
            updater.prompt_and_update(self, manifest)
        elif not silent:
            messagebox.showinfo(APP_TITLE, "최신 버전을 사용 중이에요.")

    # ---------- UI 구성 ----------
    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        individual_tab = ttk.Frame(notebook)
        profile_tab = ttk.Frame(notebook)
        alias_tab = ttk.Frame(notebook)
        settings_tab = ttk.Frame(notebook)
        notebook.add(profile_tab, text="프로필")
        notebook.add(individual_tab, text="개별 전환")
        notebook.add(alias_tab, text="장치 별칭")
        notebook.add(settings_tab, text="설정")

        self._build_individual_tab(individual_tab)
        self._build_profile_tab(profile_tab)
        self._build_alias_tab(alias_tab)
        self._build_settings_tab(settings_tab)

        self.status_var = tk.StringVar(value="")
        ttk.Label(self.root, textvariable=self.status_var, foreground="gray").pack(
            fill="x", padx=10, pady=(0, 8)
        )

    def _build_individual_tab(self, parent):
        ttk.Label(parent, text="재생 장치 (스피커 / 헤드셋 / 이어폰)", font=("", 10, "bold")).pack(
            anchor="w", pady=(12, 4), padx=10
        )
        row1 = ttk.Frame(parent)
        row1.pack(fill="x", padx=10)
        self.playback_combo = ttk.Combobox(row1, state="readonly")
        self.playback_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(row1, text="전환", command=self._on_switch_playback).pack(side="left", padx=(6, 0))

        ttk.Label(parent, text="녹음 장치 (마이크)", font=("", 10, "bold")).pack(
            anchor="w", pady=(20, 4), padx=10
        )
        row2 = ttk.Frame(parent)
        row2.pack(fill="x", padx=10)
        self.recording_combo = ttk.Combobox(row2, state="readonly")
        self.recording_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(row2, text="전환", command=self._on_switch_recording).pack(side="left", padx=(6, 0))

        ttk.Button(parent, text="장치 목록 새로고침", command=self.refresh_devices).pack(
            anchor="w", padx=10, pady=(24, 0)
        )

    def _build_profile_tab(self, parent):
        columns = ("name", "status", "playback", "recording", "hotkey")
        self.profile_tree = ttk.Treeview(parent, columns=columns, show="headings", height=10)
        self.profile_tree.heading("name", text="프로필 이름")
        self.profile_tree.heading("status", text="상태")
        self.profile_tree.heading("playback", text="재생 장치")
        self.profile_tree.heading("recording", text="녹음 장치")
        self.profile_tree.heading("hotkey", text="단축키")
        self.profile_tree.column("name", width=100)
        self.profile_tree.column("status", width=60)
        self.profile_tree.column("playback", width=170)
        self.profile_tree.column("recording", width=170)
        self.profile_tree.column("hotkey", width=80)
        self.profile_tree.pack(fill="both", expand=True, padx=10, pady=(12, 6))
        self.profile_tree.bind("<Double-1>", lambda e: self._on_apply_profile())

        self.profile_hint_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.profile_hint_var, foreground="gray").pack(anchor="w", padx=10)

        btn_row = ttk.Frame(parent)
        btn_row.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btn_row, text="전환", command=self._on_apply_profile).pack(side="left")
        ttk.Button(btn_row, text="추가", command=self._on_add_profile).pack(side="left", padx=6)
        ttk.Button(btn_row, text="수정", command=self._on_edit_profile).pack(side="left")
        ttk.Button(btn_row, text="삭제", command=self._on_delete_profile).pack(side="left", padx=6)
        ttk.Button(
            btn_row, text="현재 장치로 빠른 추가", command=self._on_quick_add_profile
        ).pack(side="left", padx=(12, 0))

        self._refresh_profile_tree()

    def _build_alias_tab(self, parent):
        ttk.Label(
            parent,
            text="장치별로 앱 안에서만 보이는 별명을 지정할 수 있어요. (Windows 실제 장치 이름은 바뀌지 않아요)",
            wraplength=480,
            foreground="gray",
        ).pack(anchor="w", padx=10, pady=(12, 8))

        self.alias_container = ttk.Frame(parent)
        self.alias_container.pack(fill="both", expand=True, padx=10)

        ttk.Button(parent, text="새로고침", command=self._refresh_alias_tab).pack(
            anchor="w", padx=10, pady=8
        )

    def _refresh_alias_tab(self):
        for w in self.alias_container.winfo_children():
            w.destroy()

        aliases = config_manager.load_aliases()
        all_devices = [("재생", d) for d in self.playback_devices] + [
            ("녹음", d) for d in self.recording_devices
        ]

        for kind, device in all_devices:
            row = ttk.Frame(self.alias_container)
            row.pack(fill="x", pady=3)
            ttk.Label(
                row, text=f"[{kind}] {device.name}", width=48, wraplength=340, anchor="w"
            ).pack(side="left")
            var = tk.StringVar(value=aliases.get(device.id, ""))
            entry = ttk.Entry(row, textvariable=var, width=16)
            entry.pack(side="left", padx=(6, 6))
            # Enter나 다른 곳을 누르면 자동 저장(바뀐 경우만)
            for event in ("<Return>", "<FocusOut>"):
                entry.bind(event, lambda e, dev=device, v=var: self._save_alias(dev, v, only_if_changed=True))
            ttk.Button(
                row, text="저장", command=lambda dev=device, v=var: self._save_alias(dev, v)
            ).pack(side="left")

    def _save_alias(self, device, var, only_if_changed=False):
        alias = var.get().strip()
        if only_if_changed and alias == config_manager.load_aliases().get(device.id, ""):
            return
        config_manager.set_alias(device.id, alias if alias else None)
        self.status_var.set(f"별칭 저장됨: {device.name} -> {alias or '(해제)'}")

    # ---------- 장치 목록 ----------
    def refresh_devices(self):
        self.playback_devices = audio_devices.get_playback_devices()
        self.recording_devices = audio_devices.get_recording_devices()

        def label(d):
            return config_manager.get_display_name(d.id, d.name)

        self.playback_combo["values"] = [label(d) for d in self.playback_devices]
        self.recording_combo["values"] = [label(d) for d in self.recording_devices]
        # 콤보에는 목록 첫 항목이 아니라 지금 쓰고 있는 기본 장치를 선택해 둔다
        for combo, devices, default_id in (
            (self.playback_combo, self.playback_devices, audio_devices.get_default_playback_id()),
            (self.recording_combo, self.recording_devices, audio_devices.get_default_recording_id()),
        ):
            ids = [d.id for d in devices]
            if default_id in ids:
                combo.current(ids.index(default_id))
            elif devices:
                combo.current(0)
        self.status_var.set(
            f"장치 {len(self.playback_devices)}개(재생) / {len(self.recording_devices)}개(녹음) 발견"
        )
        if hasattr(self, "alias_container"):
            self._refresh_alias_tab()
        self._refresh_profile_tree()

    def _on_switch_playback(self):
        idx = self.playback_combo.current()
        if idx < 0:
            return
        device = self.playback_devices[idx]
        self.switch_device(playback_id=device.id, recording_id=None)

    def _on_switch_recording(self):
        idx = self.recording_combo.current()
        if idx < 0:
            return
        device = self.recording_devices[idx]
        self.switch_device(playback_id=None, recording_id=device.id)

    # ---------- 프로필 ----------
    def _refresh_profile_tree(self):
        for row in self.profile_tree.get_children():
            self.profile_tree.delete(row)
        default_playback = audio_devices.get_default_playback_id()
        default_recording = audio_devices.get_default_recording_id()
        active_idx = config_manager.find_active_profile(self.profiles, default_playback, default_recording)
        for i, p in enumerate(self.profiles):
            self.profile_tree.insert(
                "",
                "end",
                values=(
                    p.get("name", ""),
                    "● 사용 중" if i == active_idx else "",
                    p.get("playback_name") or "-",
                    p.get("recording_name") or "-",
                    p.get("hotkey") or "-",
                ),
            )
        self.profile_hint_var.set(
            "" if self.profiles else "프로필이 없어요. '현재 장치로 빠른 추가'를 누르면 지금 쓰는 장치로 바로 만들 수 있어요."
        )
        active = self.profiles[active_idx] if active_idx is not None else None
        self._update_tray(active, default_playback, default_recording)

    def _selected_profile_index(self):
        sel = self.profile_tree.selection()
        if not sel:
            return None
        return self.profile_tree.index(sel[0])

    def _on_apply_profile(self):
        idx = self._selected_profile_index()
        if idx is None:
            return
        self.apply_profile_by_index(idx)

    def apply_profile_by_index(self, idx: int):
        if not (0 <= idx < len(self.profiles)):
            return
        p = self.profiles[idx]
        config_manager.set_last_profile(p.get("name"))  # 장치 조합이 같은 프로필 중 "사용 중"을 하나로 정하는 기준
        failed = self.switch_device(playback_id=p.get("playback_id"), recording_id=p.get("recording_id"))
        if not failed:
            self.status_var.set(f"프로필 적용됨: {p.get('name')}")

    def _on_add_profile(self):
        self._open_profile_editor()

    def _on_quick_add_profile(self):
        """지금 쓰는 재생/녹음 장치를 미리 채운 추가 창을 연다(이름만 입력하면 됨)."""
        current_playback_id = audio_devices.get_default_playback_id()
        current_recording_id = audio_devices.get_default_recording_id()
        self._open_profile_editor(
            prefill_playback_id=current_playback_id,
            prefill_recording_id=current_recording_id,
        )

    def _on_edit_profile(self):
        idx = self._selected_profile_index()
        if idx is None:
            messagebox.showinfo(APP_TITLE, "수정할 프로필을 선택하세요.")
            return
        self._open_profile_editor(edit_index=idx)

    def _on_delete_profile(self):
        idx = self._selected_profile_index()
        if idx is None:
            return
        if messagebox.askyesno(APP_TITLE, "선택한 프로필을 삭제할까요?"):
            config_manager.delete_profile(idx)
            self.profiles = config_manager.load_profiles()
            self._refresh_profile_tree()
            self._register_hotkeys()

    def open_profile_editor_with_draft(self, edit_index: int | None, draft: dict):
        """팝업 폼에서 입력하던 값(draft)을 이어받아 편집기를 연다."""
        self._open_profile_editor(edit_index=edit_index, draft=draft)

    def _open_profile_editor(
        self,
        edit_index: int | None = None,
        prefill_playback_id: str | None = None,
        prefill_recording_id: str | None = None,
        draft: dict | None = None,
    ):
        self.show_from_tray()

        editor = tk.Toplevel(self.root)
        editor.title("프로필 편집" if edit_index is not None else "프로필 추가")
        editor.transient(self.root)
        editor.grab_set()
        self._center_window(editor, 380, 500)

        existing = self.profiles[edit_index] if edit_index is not None else {}
        existing = {**existing, **(draft or {})}

        ttk.Label(editor, text="이름").pack(anchor="w", padx=12, pady=(12, 0))
        name_var = tk.StringVar(value=existing.get("name", ""))
        name_entry = ttk.Entry(editor, textvariable=name_var)
        name_entry.pack(fill="x", padx=12)
        if prefill_playback_id or prefill_recording_id:
            # 빠른 추가: 이름을 바로 입력할 수 있게 포커스를 준다
            editor.after(50, lambda: (name_entry.focus_set(), name_entry.select_range(0, "end")))

        ttk.Label(editor, text="아이콘").pack(anchor="w", padx=12, pady=(12, 0))
        # 저장 값은 영문 키("headset" 등), 화면에는 한글 이름을 보여준다
        icon_labels = tray_popup_web.PROFILE_ICON_LABELS
        icon_var = tk.StringVar(value=icon_labels.get(existing.get("icon"), icon_labels["default"]))
        icon_combo = ttk.Combobox(
            editor, textvariable=icon_var, state="readonly", values=list(icon_labels.values())
        )
        icon_combo.pack(fill="x", padx=12)

        # 새로 고른 이미지는 저장을 누를 때까지 메모리에만 둔다(취소해도 파일이 남지 않게)
        icon_state = {"name": existing.get("icon_image"), "new_image": None}
        icon_row = ttk.Frame(editor)
        icon_row.pack(fill="x", padx=12, pady=(8, 0))
        preview_big = ttk.Label(icon_row)
        preview_big.pack(side="left")
        preview_small = ttk.Label(icon_row)  # 트레이에서 실제로 보일 16px 크기
        preview_small.pack(side="left", padx=(8, 12))

        def refresh_preview():
            kind = next((k for k, v in icon_labels.items() if v == icon_var.get()), "default")
            img = (
                icon_state["new_image"]
                or icon_store.load_icon_image(icon_state["name"])
                or icon_art.draw_profile_icon(kind, 64)
            )
            for label, size in ((preview_big, 40), (preview_small, 16)):
                label.image = ImageTk.PhotoImage(img.resize((size, size)))  # 참조를 붙들어 둬야 사라지지 않는다
                label.configure(image=label.image)

        def on_pick_file():
            path = filedialog.askopenfilename(
                parent=editor, filetypes=[("이미지", "*.png *.jpg *.jpeg *.bmp *.gif *.ico")]
            )
            if not path:
                return
            try:
                icon_state["new_image"] = icon_store.open_image_file(path)
            except Exception:
                messagebox.showwarning(APP_TITLE, "이미지를 열 수 없어요. PNG나 JPG 파일을 골라 주세요.", parent=editor)
                return
            refresh_preview()

        def on_paste_image():
            img = icon_store.get_clipboard_image()
            if img is None:
                messagebox.showinfo(
                    APP_TITLE, "클립보드에 이미지가 없어요. 이미지를 복사한 뒤 다시 눌러 주세요.", parent=editor
                )
                return
            icon_state["new_image"] = img
            refresh_preview()

        def on_clear_image():
            icon_state["name"] = None
            icon_state["new_image"] = None
            refresh_preview()

        ttk.Button(icon_row, text="이미지 선택", command=on_pick_file).pack(side="left")
        ttk.Button(icon_row, text="붙여넣기", command=on_paste_image).pack(side="left", padx=4)
        ttk.Button(icon_row, text="지우기", command=on_clear_image).pack(side="left")
        ttk.Label(
            editor,
            text="왼쪽은 확대 미리보기, 오른쪽 작은 그림은 작업 표시줄 트레이에서 실제로 보이는 크기예요. "
                 "팝업의 프로필 타일에도 쓰여요.",
            wraplength=340, foreground="gray",
        ).pack(anchor="w", padx=12)
        ttk.Label(
            editor,
            text="단순한 모양이 가장 또렷해요. 투명 배경은 붙여넣기에서는 유지되지 않으니 PNG 파일로 선택하세요.",
            wraplength=340, foreground="gray",
        ).pack(anchor="w", padx=12, pady=(4, 0))
        icon_combo.bind("<<ComboboxSelected>>", lambda e: on_clear_image())  # 기본 아이콘을 고르면 내 이미지는 해제
        refresh_preview()

        playback_label_row = ttk.Frame(editor)
        playback_label_row.pack(fill="x", padx=12, pady=(12, 0))
        ttk.Label(playback_label_row, text="재생 장치").pack(side="left")
        playback_combo = ttk.Combobox(editor, state="readonly")
        playback_combo["values"] = [
            config_manager.get_display_name(d.id, d.name) for d in self.playback_devices
        ]
        playback_combo.pack(fill="x", padx=12)
        playback_idx_by_id = {d.id: i for i, d in enumerate(self.playback_devices)}
        existing_playback = existing.get("playback_name")
        if prefill_playback_id and prefill_playback_id in playback_idx_by_id:
            playback_combo.current(playback_idx_by_id[prefill_playback_id])
            ttk.Label(
                playback_label_row, text=" · 현재 사용 중", foreground="#0f6e56"
            ).pack(side="left")
        elif existing_playback in playback_combo["values"]:
            playback_combo.set(existing_playback)
        elif self.playback_devices:
            playback_combo.current(0)

        recording_label_row = ttk.Frame(editor)
        recording_label_row.pack(fill="x", padx=12, pady=(12, 0))
        ttk.Label(recording_label_row, text="녹음 장치").pack(side="left")
        recording_combo = ttk.Combobox(editor, state="readonly")
        recording_combo["values"] = [
            config_manager.get_display_name(d.id, d.name) for d in self.recording_devices
        ]
        recording_combo.pack(fill="x", padx=12)
        recording_idx_by_id = {d.id: i for i, d in enumerate(self.recording_devices)}
        existing_recording = existing.get("recording_name")
        if prefill_recording_id and prefill_recording_id in recording_idx_by_id:
            recording_combo.current(recording_idx_by_id[prefill_recording_id])
            ttk.Label(
                recording_label_row, text=" · 현재 사용 중", foreground="#0f6e56"
            ).pack(side="left")
        elif existing_recording in recording_combo["values"]:
            recording_combo.set(existing_recording)
        elif self.recording_devices:
            recording_combo.current(0)

        ttk.Label(editor, text="단축키 (예: ctrl+alt+1, 비워두면 없음)").pack(
            anchor="w", padx=12, pady=(12, 0)
        )
        hotkey_var = tk.StringVar(value=existing.get("hotkey", "") or "")
        ttk.Entry(editor, textvariable=hotkey_var).pack(fill="x", padx=12)

        def on_save():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning(APP_TITLE, "이름을 입력하세요.")
                return
            p_idx = playback_combo.current()
            r_idx = recording_combo.current()
            playback_dev = self.playback_devices[p_idx] if p_idx >= 0 else None
            recording_dev = self.recording_devices[r_idx] if r_idx >= 0 else None
            hotkey = hotkey_var.get().strip() or None
            error = self.hotkey_error(hotkey)
            if error:
                messagebox.showwarning(APP_TITLE, error)
                return

            profile = {
                "name": name,
                "icon": next((k for k, v in icon_labels.items() if v == icon_var.get()), "default"),
                "playback_id": playback_dev.id if playback_dev else None,
                "playback_name": playback_combo.get() if playback_dev else None,
                "recording_id": recording_dev.id if recording_dev else None,
                "recording_name": recording_combo.get() if recording_dev else None,
                "hotkey": hotkey,
            }
            if icon_state["new_image"] is not None:
                profile["icon_image"] = icon_store.save_icon_image(icon_state["new_image"])
            elif icon_state["name"]:
                profile["icon_image"] = icon_state["name"]

            if edit_index is not None:
                config_manager.update_profile(edit_index, profile)
            else:
                config_manager.add_profile(profile)

            self.profiles = config_manager.load_profiles()
            self._refresh_profile_tree()
            self._register_hotkeys()
            editor.destroy()

        ttk.Button(editor, text="저장", command=on_save).pack(pady=16)

    @staticmethod
    def _center_window(win: tk.Toplevel, width: int, height: int):
        win.update_idletasks()
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        win.geometry(f"{width}x{height}+{x}+{y}")

    # ---------- 글로벌 단축키 ----------
    @staticmethod
    def hotkey_error(hotkey: str | None) -> str | None:
        """단축키 형식이 틀리면 안내 문구를, 올바르거나 비어 있으면 None을 돌려준다."""
        if not hotkey:
            return None
        try:
            keyboard.parse_hotkey(hotkey)
        except Exception:
            return "단축키 형식이 올바르지 않아요. 예: ctrl+alt+1"
        return None

    def _register_hotkeys(self):
        try:
            keyboard.unhook_all_hotkeys()
        except AttributeError:
            pass  # 키보드 리스너가 아직 초기화되기 전
        for idx, p in enumerate(self.profiles):
            hotkey = p.get("hotkey")
            if not hotkey:
                continue
            try:
                keyboard.add_hotkey(hotkey, self._make_hotkey_callback(idx))
            except Exception:
                pass

    def _make_hotkey_callback(self, idx: int):
        def callback():
            self.root.after(0, lambda: self.apply_profile_by_index(idx))

        return callback

    # ---------- 트레이 아이콘 ----------
    def _start_tray_thread(self):
        show_popup_item = pystray.MenuItem("빠른 전환", self._open_tray_popup, default=True, visible=False)
        open_item = pystray.MenuItem("열기", lambda: self.root.after(0, self.show_from_tray))
        quit_item = pystray.MenuItem("종료", lambda: self.root.after(0, self.quit_app))
        menu = pystray.Menu(show_popup_item, open_item, pystray.Menu.SEPARATOR, quit_item)

        self.tray_icon = pystray.Icon("hsswitch", icon_art.draw_headset_mic(64), APP_TITLE, menu)

        def run_tray(retry=True):
            try:
                comtypes.CoInitialize()
            except Exception:
                pass
            try:
                self.tray_icon.run(setup=self._on_tray_ready)
            except Exception:
                self._log_error("tray_icon.run() failed")
                if retry:
                    # 업데이트 직후 재시작처럼 트레이 등록 타이밍이 꼬일 수 있어 한 번만 재시도
                    time.sleep(2)
                    run_tray(retry=False)

        threading.Thread(target=run_tray, daemon=True).start()

    def _on_tray_ready(self, icon):
        """트레이 스레드에서 호출된다. pystray는 아이콘이 표시된 뒤에만 아이콘 변경을 반영하므로
        표시된 다음에 현재 상태(사용 중인 프로필의 아이콘/툴팁)를 한 번 맞춘다."""
        icon.visible = True  # setup을 직접 넘기면 pystray가 표시해 주지 않는다
        self._tray_key = None
        self.root.after(0, self._refresh_profile_tree)

    def _update_tray(self, active, default_playback, default_recording):
        """트레이 아이콘/툴팁을 지금 상태로 맞춘다. 사용 중인 프로필이 없으면 기본 아이콘과 기본 장치 이름."""
        if not self.tray_icon:
            return
        if active:
            title = f"{APP_TITLE} · 사용 중: {active.get('name')}"
            icon_key = (active.get("icon"), active.get("icon_image"))
        else:
            icon_key = (None, None)
            names = {
                d.id: config_manager.get_display_name(d.id, d.name)
                for d in self.playback_devices + self.recording_devices
            }
            title = (
                f"{APP_TITLE} · 재생: {names.get(default_playback, '-')}"
                f" / 녹음: {names.get(default_recording, '-')}"
            )
        title = title[:127]  # Windows 트레이 툴팁은 127자까지
        if (title, icon_key) != self._tray_key:
            self._tray_key = (title, icon_key)
            image = icon_store.load_icon_image(icon_key[1]) or icon_art.draw_profile_icon(icon_key[0], 64)
            self.tray_icon.icon = image
            self.tray_icon.title = title

    @staticmethod
    def _log_error(message: str):
        try:
            log_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "HSSwitch")
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "crash.log"), "a", encoding="utf-8") as f:
                f.write(f"{message}\n{traceback.format_exc()}\n\n")
        except Exception:
            pass

    def _open_tray_popup(self, icon=None, item=None):
        self.root.after(0, self._show_tray_popup)

    def _show_tray_popup(self):
        self.refresh_devices()
        tray_popup_web.show_tray_popup_web(self)

    def hide_to_tray(self):
        self.root.withdraw()

    def show_from_tray(self):
        self.root.deiconify()
        self.root.lift()

    def quit_app(self):
        try:
            keyboard.unhook_all_hotkeys()
        except AttributeError:
            pass
        if self.tray_icon:
            self.tray_icon.stop()
        tray_popup_web.shutdown()
        self.root.after(0, self.root.destroy)


def main():
    if not _ensure_single_instance():
        return

    ready = threading.Event()
    holder = {}

    def tk_thread():
        # Tk()는 만든 스레드에서만 mainloop을 돌릴 수 있다.
        # 초기화 중 예외가 나도 ready는 반드시 세팅해야 한다. 아니면 main()이 ready.wait()에서
        # 영원히 멈춰 앱이 아무 반응 없이 실행 안 된 것처럼 보인다.
        try:
            comtypes.CoInitialize()
            root = tk.Tk()
            app = HSSwitchApp(root)
            if "--startup" in sys.argv:
                app.hide_to_tray()
            holder["app"] = app
        except Exception:
            holder["error"] = traceback.format_exc()
        finally:
            ready.set()

        if "app" in holder:
            root.mainloop()

    threading.Thread(target=tk_thread, daemon=True).start()
    ready.wait()

    if "error" in holder:
        try:
            log_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "HSSwitch")
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "crash.log"), "w", encoding="utf-8") as f:
                f.write(holder["error"])
        except Exception:
            pass
        return

    app = holder["app"]

    # pywebview는 창 생성/이벤트 루프를 진짜 메인 스레드에서 실행해야 한다
    comtypes.CoInitialize()
    tray_popup_web.init_window(app)
    tray_popup_web.run_event_loop()


if __name__ == "__main__":
    main()
