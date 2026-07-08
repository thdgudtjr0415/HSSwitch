"""
HSSwitch — 스피커/헤드셋/마이크 빠른 전환 프로그램

- 메인 창: 개별 전환 / 프로필 / 장치 별칭 / 설정 탭 (다크모드는 트레이 팝업에만 적용)
- 트레이 아이콘 좌클릭: pywebview 팝업(tray_popup_web.py)으로 프로필/장치 빠른 전환
- 트레이 아이콘 우클릭: 열기/종료
- 전환 시 Console/Multimedia/Communications 세 역할 모두 갱신
"""

import ctypes
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import comtypes
import keyboard
import pystray

import audio_devices
import config_manager
import icon_art
import startup_manager
import tray_popup_web
import updater
from policy_config import set_default_device
from version import APP_VERSION

APP_TITLE = "HSSwitch"
PROFILE_ICONS = ["headset", "speaker", "mic", "default"]

_SINGLE_INSTANCE_MUTEX_NAME = "Global\\HSSwitchSingleInstanceMutex"
_instance_mutex_handle = None  # GC/프로세스 종료 전까지 살려둬야 뮤텍스가 유지됨


def _ensure_single_instance() -> bool:
    """
    이미 실행 중인 인스턴스가 있으면 그 창을 앞으로 가져오고 False를 반환한다.
    (exe 사본을 여러 개 실행하거나, 업데이트 재실행 타이밍이 겹칠 때 트레이 아이콘이
    여러 개 뜨는 걸 방지)
    """
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


def switch_device(playback_id: str | None, recording_id: str | None):
    if playback_id:
        set_default_device(playback_id)
    if recording_id:
        set_default_device(recording_id)


class HSSwitchApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("540x500")
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        try:
            ttk.Style(self.root).theme_use("vista")
        except tk.TclError:
            pass  # "vista" 테마는 Windows 전용, 없는 환경이면 기본 테마로 조용히 폴백

        self.audio_module = audio_devices
        self.playback_devices: list[audio_devices.DeviceInfo] = []
        self.recording_devices: list[audio_devices.DeviceInfo] = []
        self.profiles: list[dict] = config_manager.load_profiles()

        # 다른 스레드에서 tkinter 위젯을 직접 호출하면 안 되므로 미리 캐싱
        self.screen_width = root.winfo_screenwidth()
        self.screen_height = root.winfo_screenheight()

        self._build_ui()
        self.refresh_devices()
        self._register_hotkeys()

        self.tray_icon = None
        self._start_tray_thread()

        # 시작하자마자 확인하면 창 뜨는 타이밍과 겹치니 살짝 늦춰서 백그라운드 확인.
        # "자동 업데이트 확인"이 꺼져 있으면 시작할 때는 아예 확인하지 않는다
        # (설정 탭의 수동 "업데이트 확인" 버튼은 이 설정과 무관하게 항상 동작한다).
        if config_manager.load_auto_update_check():
            self.root.after(2000, lambda: self._check_for_update(silent=True))

    def switch_device(self, playback_id, recording_id):
        switch_device(playback_id, recording_id)
        name = ""
        if playback_id:
            name = self._name_for(self.playback_devices, playback_id)
        if recording_id:
            name = self._name_for(self.recording_devices, recording_id)
        self.status_var.set(f"전환됨: {name}")

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
        notebook.add(individual_tab, text="개별 전환")
        notebook.add(profile_tab, text="프로필")
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
        columns = ("name", "playback", "recording", "hotkey")
        self.profile_tree = ttk.Treeview(parent, columns=columns, show="headings", height=10)
        self.profile_tree.heading("name", text="프로필 이름")
        self.profile_tree.heading("playback", text="재생 장치")
        self.profile_tree.heading("recording", text="녹음 장치")
        self.profile_tree.heading("hotkey", text="단축키")
        self.profile_tree.column("name", width=100)
        self.profile_tree.column("playback", width=140)
        self.profile_tree.column("recording", width=140)
        self.profile_tree.column("hotkey", width=90)
        self.profile_tree.pack(fill="both", expand=True, padx=10, pady=(12, 6))
        self.profile_tree.bind("<Double-1>", lambda e: self._on_apply_profile())

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

        self._alias_vars = {}
        for kind, device in all_devices:
            row = ttk.Frame(self.alias_container)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=f"[{kind}] {device.name}", width=38, anchor="w").pack(side="left")
            var = tk.StringVar(value=aliases.get(device.id, ""))
            self._alias_vars[device.id] = var
            ttk.Entry(row, textvariable=var, width=20).pack(side="left", padx=(6, 6))
            ttk.Button(
                row, text="저장", command=lambda dev=device, v=var: self._save_alias(dev, v)
            ).pack(side="left")

    def _save_alias(self, device, var):
        alias = var.get().strip()
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
        if self.playback_devices:
            self.playback_combo.current(0)
        if self.recording_devices:
            self.recording_combo.current(0)
        self.status_var.set(
            f"장치 {len(self.playback_devices)}개(재생) / {len(self.recording_devices)}개(녹음) 발견"
        )
        if hasattr(self, "alias_container"):
            self._refresh_alias_tab()

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
        for p in self.profiles:
            self.profile_tree.insert(
                "",
                "end",
                values=(
                    p.get("name", ""),
                    p.get("playback_name", "-"),
                    p.get("recording_name", "-"),
                    p.get("hotkey", "-"),
                ),
            )

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
        self.switch_device(playback_id=p.get("playback_id"), recording_id=p.get("recording_id"))
        self.status_var.set(f"프로필 적용됨: {p.get('name')}")

    def _on_add_profile(self):
        self._open_profile_editor()

    def _on_quick_add_profile(self):
        """지금 실제로 쓰고 있는 재생/녹음 장치를 그대로 채운 채로 추가 창을 연다.
        드롭다운에서 장치를 직접 고를 필요 없이 이름만 입력하면 끝."""
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

    def _open_profile_editor(
        self,
        edit_index: int | None = None,
        prefill_playback_id: str | None = None,
        prefill_recording_id: str | None = None,
    ):
        self.show_from_tray()

        editor = tk.Toplevel(self.root)
        editor.title("프로필 편집" if edit_index is not None else "프로필 추가")
        editor.transient(self.root)
        editor.grab_set()
        self._center_window(editor, 360, 320)

        existing = self.profiles[edit_index] if edit_index is not None else {}

        name_entry_row = ttk.Label(editor, text="이름")
        name_entry_row.pack(anchor="w", padx=12, pady=(12, 0))
        name_var = tk.StringVar(value=existing.get("name", ""))
        name_entry = ttk.Entry(editor, textvariable=name_var)
        name_entry.pack(fill="x", padx=12)
        if prefill_playback_id or prefill_recording_id:
            # 빠른 추가: 이름만 바로 입력할 수 있도록 포커스를 준다.
            editor.after(50, lambda: (name_entry.focus_set(), name_entry.select_range(0, "end")))

        ttk.Label(editor, text="아이콘").pack(anchor="w", padx=12, pady=(12, 0))
        icon_var = tk.StringVar(value=existing.get("icon", "default"))
        icon_combo = ttk.Combobox(
            editor, textvariable=icon_var, state="readonly", values=PROFILE_ICONS
        )
        icon_combo.pack(fill="x", padx=12)

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

            profile = {
                "name": name,
                "icon": icon_var.get() or "default",
                "playback_id": playback_dev.id if playback_dev else None,
                "playback_name": playback_combo.get() if playback_dev else None,
                "recording_id": recording_dev.id if recording_dev else None,
                "recording_name": recording_combo.get() if recording_dev else None,
                "hotkey": hotkey,
            }

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
    def _register_hotkeys(self):
        try:
            keyboard.unhook_all_hotkeys()
        except AttributeError:
            pass  # 첫 실행 등 리스너 초기화 전 상태, 무시해도 안전
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
    def _make_tray_image(self):
        return icon_art.draw_headset_mic(64)

    def _start_tray_thread(self):
        show_popup_item = pystray.MenuItem("빠른 전환", self._open_tray_popup, default=True, visible=False)
        open_item = pystray.MenuItem("열기", lambda: self.root.after(0, self.show_from_tray))
        quit_item = pystray.MenuItem("종료", lambda: self.root.after(0, self.quit_app))
        menu = pystray.Menu(show_popup_item, open_item, pystray.Menu.SEPARATOR, quit_item)

        self.tray_icon = pystray.Icon("hsswitch", self._make_tray_image(), APP_TITLE, menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

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
        # Tk()는 자신을 생성한 스레드에서만 mainloop을 돌릴 수 있다
        comtypes.CoInitialize()
        root = tk.Tk()
        app = HSSwitchApp(root)
        if "--startup" in sys.argv:
            app.hide_to_tray()
        holder["app"] = app
        ready.set()
        root.mainloop()

    threading.Thread(target=tk_thread, daemon=True).start()
    ready.wait()
    app = holder["app"]

    # pywebview는 창 생성/이벤트 루프를 진짜 메인 스레드에서 실행해야 한다
    comtypes.CoInitialize()
    tray_popup_web.init_window(app)
    tray_popup_web.run_event_loop()


if __name__ == "__main__":
    main()
