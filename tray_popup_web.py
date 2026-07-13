"""
트레이 아이콘 클릭 시 뜨는 팝업을 pywebview로 렌더링.
클릭할 때마다 새 창을 만들고, 닫힐 때 완전히 폐기한다.
"""

import ctypes

import webview

import audio_devices
import config_manager
import theme_manager
import volume_control

ICONS = {
    "headset": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M4 13v-1a8 8 0 0 1 16 0v1"/>'
        '<rect x="2.5" y="13" width="5" height="7" rx="2"/>'
        '<rect x="16.5" y="13" width="5" height="7" rx="2"/></svg>'
    ),
    "speaker": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M17 8.5a5 5 0 0 1 0 7"/></svg>'
    ),
    "speaker_muted": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M4 9v6h4l5 4V5L8 9H4z"/><line x1="16" y1="9" x2="21" y2="14"/>'
        '<line x1="21" y1="9" x2="16" y2="14"/></svg>'
    ),
    "mic": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="9" y="2" width="6" height="12" rx="3"/>'
        '<path d="M5 11a7 7 0 0 0 14 0"/>'
        '<line x1="12" y1="18" x2="12" y2="22"/><line x1="8" y1="22" x2="16" y2="22"/></svg>'
    ),
    "plus": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round">'
        '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>'
    ),
    "check": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="4 12 9 17 20 6"/></svg>'
    ),
    "default": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">'
        '<circle cx="12" cy="12" r="8"/></svg>'
    ),
}

PROFILE_ICON_KEYS = ("default", "headset", "speaker", "mic")


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


class Api:
    """JS(pywebview.api.*)에서 호출하는 파이썬 쪽 진입점. 실제 처리는 tkinter 메인 스레드로 위임."""

    def __init__(self, app, holder):
        self.app = app
        self.holder = holder  # {"window": <이 팝업 전용 webview.Window 인스턴스>}

    def switch_playback(self, device_id):
        self.app.root.after(0, lambda: self.app.switch_device(playback_id=device_id, recording_id=None))
        self._close()

    def switch_recording(self, device_id):
        self.app.root.after(0, lambda: self.app.switch_device(playback_id=None, recording_id=device_id))
        self._close()

    def apply_profile(self, idx):
        self.app.root.after(0, lambda: self.app.apply_profile_by_index(int(idx)))
        self._close()

    def get_main_view(self):
        """프로필 추가 폼에서 '뒤로'/저장 완료 시 메인 화면 HTML을 다시 만들어 돌려준다.
        팝업이 떠 있는 동안 창 크기/위치가 갑자기 바뀌면 화면에서 튀어 보이므로,
        처음 열었을 때 계산된 크기/위치를 그대로 유지하고 다시 계산하지 않는다."""
        return _build_main_view_html(self.app)

    def get_add_form(self):
        """'+ 추가' 타일을 눌렀을 때 지금 쓰고 있는 재생/녹음 장치를 미리 채운 입력 폼 HTML."""
        return _build_profile_form_html(self.app)

    def get_edit_form(self, idx):
        """프로필 우클릭 -> 수정을 눌렀을 때, 그 프로필의 저장된 값을 채운 입력 폼 HTML."""
        return _build_profile_form_html(self.app, edit_index=int(idx))

    def save_new_profile(self, name, icon, playback_id, recording_id, hotkey):
        name = (name or "").strip()
        if not name:
            return {"ok": False, "error": "이름을 입력하세요."}

        profile = self._build_profile_dict(name, icon, playback_id, recording_id, hotkey)
        config_manager.add_profile(profile)
        self._refresh_app()
        return {"ok": True}

    def update_profile(self, idx, name, icon, playback_id, recording_id, hotkey):
        name = (name or "").strip()
        if not name:
            return {"ok": False, "error": "이름을 입력하세요."}

        profile = self._build_profile_dict(name, icon, playback_id, recording_id, hotkey)
        config_manager.update_profile(int(idx), profile)
        self._refresh_app()
        return {"ok": True}

    def delete_profile(self, idx):
        config_manager.delete_profile(int(idx))
        self._refresh_app()
        return {"ok": True}

    def _build_profile_dict(self, name, icon, playback_id, recording_id, hotkey):
        playback_dev = next((d for d in self.app.playback_devices if d.id == playback_id), None)
        recording_dev = next((d for d in self.app.recording_devices if d.id == recording_id), None)
        return {
            "name": name,
            "icon": icon if icon in PROFILE_ICON_KEYS else "default",
            "playback_id": playback_dev.id if playback_dev else None,
            "playback_name": config_manager.get_display_name(playback_dev.id, playback_dev.name)
            if playback_dev else None,
            "recording_id": recording_dev.id if recording_dev else None,
            "recording_name": config_manager.get_display_name(recording_dev.id, recording_dev.name)
            if recording_dev else None,
            "hotkey": (hotkey or "").strip() or None,
        }

    def _refresh_app(self):
        def _refresh():
            self.app.profiles = config_manager.load_profiles()
            self.app._register_hotkeys()

        self.app.root.after(0, _refresh)

    def set_volume(self, device_id, percent):
        volume_control.set_volume_percent(device_id, int(float(percent)))

    def toggle_mute(self, device_id):
        return volume_control.toggle_mute(device_id)

    def close(self):
        self._close()

    def _close(self):
        window = self.holder.get("window")
        if window is not None:
            try:
                window.destroy()
            except Exception:
                pass
            self.holder["window"] = None


def _device_rows_html(devices, default_id, kind):
    rows = ""
    for i, d in enumerate(devices):
        name = _esc(config_manager.get_display_name(d.id, d.name))
        active = d.id == default_id
        if kind == "playback":
            icon_kind = "headset" if ("헤드" in d.name or "head" in d.name.lower()) else "speaker"
            call = f"pywebview.api.switch_playback('{d.id}')"
        else:
            icon_kind = "mic"
            call = f"pywebview.api.switch_recording('{d.id}')"
        check = f'<span class="check">{ICONS["check"]}</span>' if active else ""
        border_cls = "" if i == 0 else "border-top"
        rows += f'''
        <div class="row {border_cls}" onclick="{call}">
          <span class="row-icon">{ICONS[icon_kind]}</span>
          <span class="row-label">{name}</span>
          {check}
        </div>'''
    return rows


def _volume_slider_html(device_id, key):
    if not device_id:
        return ""
    current = volume_control.get_volume_percent(device_id)
    is_muted = volume_control.get_mute(device_id)
    bubble_id = f"vol_bubble_{key}"
    icon_id = f"vol_icon_{key}"
    slider_id = f"vol_slider_{key}"
    num_id = f"vol_num_{key}"
    muted_cls = "muted" if is_muted else ""
    return f'''
    <div class="volume-row">
      <span class="vol-icon-btn {muted_cls}" id="{icon_id}" onclick="hswToggleMute('{device_id}', '{key}')">
        <span class="icon-on">{ICONS["speaker"]}</span>
        <span class="icon-off">{ICONS["speaker_muted"]}</span>
      </span>
      <div class="slider-wrap">
        <input type="range" min="0" max="100" value="{current}" class="slider" id="{slider_id}"
               oninput="hswVolInput(this, '{device_id}', '{bubble_id}', '{num_id}')"
               onmouseup="hswVolEnd('{bubble_id}')" ontouchend="hswVolEnd('{bubble_id}')">
        <span class="vol-bubble" id="{bubble_id}">{current}</span>
      </div>
      <input type="text" inputmode="numeric" maxlength="3" value="{current}" class="vol-num" id="{num_id}"
             onchange="hswVolNumInput(this, '{device_id}', '{slider_id}')">
    </div>'''


def _build_main_view_html(app) -> str:
    profiles = config_manager.load_profiles()
    default_playback = audio_devices.get_default_playback_id()
    default_recording = audio_devices.get_default_recording_id()

    profile_tiles = ""
    for idx, prof in enumerate(profiles):
        icon_kind = prof.get("icon") if prof.get("icon") in ("headset", "speaker", "mic") else "default"
        profile_tiles += f'''
        <div class="tile" onclick="pywebview.api.apply_profile({idx})"
             oncontextmenu="hswOnProfileContextMenu(event, {idx})">
          <span class="tile-icon">{ICONS[icon_kind]}</span>
          <span class="tile-label">{_esc(prof.get("name", ""))}</span>
        </div>'''
    profile_tiles += f'''
        <div class="tile add" onclick="hswShowAdd()">
          <span class="tile-icon">{ICONS["plus"]}</span>
          <span class="tile-label">추가</span>
        </div>'''

    empty_note = (
        "" if profiles else '<div class="empty-note">저장된 프로필이 없어요. 눌러서 추가해보세요.</div>'
    )

    return f'''
      <div class="section-label">프로필</div>
      <div class="grid">{profile_tiles}</div>
      {empty_note}

      <div class="section-label">재생 장치</div>
      <div class="card">{_device_rows_html(app.playback_devices, default_playback, "playback")}</div>
      {_volume_slider_html(default_playback, "playback")}

      <div class="section-label">녹음 장치</div>
      <div class="card">{_device_rows_html(app.recording_devices, default_recording, "recording")}</div>
      {_volume_slider_html(default_recording, "recording")}
    '''


def _build_profile_form_html(app, edit_index: int | None = None) -> str:
    """'+ 추가' 또는 프로필 우클릭 -> 수정을 눌렀을 때 보여줄 입력 폼.
    추가 모드에서는 지금 실제로 쓰고 있는 재생/녹음 장치를 미리 선택해두고,
    수정 모드에서는 그 프로필에 저장돼 있던 값을 채운다."""
    profiles = config_manager.load_profiles()
    existing = (
        profiles[edit_index] if edit_index is not None and 0 <= edit_index < len(profiles) else None
    )

    default_playback = audio_devices.get_default_playback_id()
    default_recording = audio_devices.get_default_recording_id()
    selected_playback_id = existing.get("playback_id") if existing else default_playback
    selected_recording_id = existing.get("recording_id") if existing else default_recording

    playback_options = ""
    for d in app.playback_devices:
        label = _esc(config_manager.get_display_name(d.id, d.name))
        selected = "selected" if d.id == selected_playback_id else ""
        playback_options += f'<option value="{d.id}" {selected}>{label}</option>'

    recording_options = ""
    for d in app.recording_devices:
        label = _esc(config_manager.get_display_name(d.id, d.name))
        selected = "selected" if d.id == selected_recording_id else ""
        recording_options += f'<option value="{d.id}" {selected}>{label}</option>'

    playback_hint = (
        ' <span class="current-hint">· 현재 사용 중</span>'
        if selected_playback_id and selected_playback_id == default_playback else ""
    )
    recording_hint = (
        ' <span class="current-hint">· 현재 사용 중</span>'
        if selected_recording_id and selected_recording_id == default_recording else ""
    )
    existing_icon = existing.get("icon", "default") if existing else "default"
    icon_options = "".join(
        f'<option value="{k}" {"selected" if existing_icon == k else ""}>{k}</option>'
        for k in PROFILE_ICON_KEYS
    )

    title = "프로필 수정" if existing is not None else "프로필 추가"
    name_value = _esc(existing.get("name", "")) if existing else ""
    hotkey_value = _esc(existing.get("hotkey") or "") if existing else ""
    edit_index_value = edit_index if existing is not None else ""

    return f'''
      <div class="form-header">
        <span class="back-btn" onclick="hswShowMain()">‹ 뒤로</span>
        <span class="form-title">{title}</span>
      </div>
      <input type="hidden" id="add-edit-index" value="{edit_index_value}">
      <div class="field">
        <div class="field-label">이름</div>
        <input type="text" id="add-name" class="text-input" placeholder="예: 게임할 때" value="{name_value}">
      </div>
      <div class="field">
        <div class="field-label">아이콘</div>
        <select id="add-icon" class="select-input">{icon_options}</select>
      </div>
      <div class="field">
        <div class="field-label">재생 장치{playback_hint}</div>
        <select id="add-playback" class="select-input">{playback_options}</select>
      </div>
      <div class="field">
        <div class="field-label">녹음 장치{recording_hint}</div>
        <select id="add-recording" class="select-input">{recording_options}</select>
      </div>
      <div class="field">
        <div class="field-label">단축키 (예: ctrl+alt+1, 비워두면 없음)</div>
        <input type="text" id="add-hotkey" class="text-input" placeholder="" value="{hotkey_value}">
      </div>
      <div class="save-row">
        <button class="save-btn" onclick="hswSaveProfile()">저장</button>
      </div>
      <div class="error-msg" id="add-error"></div>
    '''


def _build_html(app) -> str:
    resolved = theme_manager.resolve_theme()
    p = theme_manager.get_palette(resolved)
    main_view = _build_main_view_html(app)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; height: 100%; background: {p['popup_bg']}; overflow: hidden; }}
  body {{
    font-family: -apple-system, 'Segoe UI', 'Helvetica Neue', sans-serif;
    user-select: none; -webkit-user-select: none;
    padding: 16px; color: {p['fg']};
  }}
  .section-label {{
    font-size: 11px; font-weight: 600; color: {p['fg_muted']};
    letter-spacing: 0.3px; margin: 14px 0 8px;
  }}
  .section-label:first-child {{ margin-top: 0; }}
  .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }}
  .tile {{
    background: {p['card_bg']}; border-radius: 16px; height: 76px; display: flex;
    flex-direction: column; align-items: center; justify-content: center; gap: 6px;
    cursor: pointer; transition: background 0.1s;
  }}
  .tile:hover {{ background: {p['card_hover']}; }}
  .tile.add {{ color: {p['fg_muted']}; }}
  .tile-icon svg {{ width: 20px; height: 20px; color: {p['fg']}; display: block; }}
  .tile.add .tile-icon svg {{ color: {p['fg_muted']}; }}
  .tile-label {{ font-size: 10.5px; }}
  .empty-note {{ font-size: 11px; color: {p['fg_muted']}; margin-top: 6px; }}
  .card {{ background: {p['card_bg']}; border-radius: 14px; overflow: hidden; }}
  .row {{ display: flex; align-items: center; gap: 10px; padding: 10px 14px; cursor: pointer; }}
  .row.border-top {{ border-top: 0.5px solid {p['divider']}; }}
  .row:hover {{ background: {p['card_hover']}; }}
  .row-icon svg {{ width: 16px; height: 16px; color: {p['fg']}; display: block; }}
  .row-label {{ font-size: 13px; flex: 1; }}
  .check svg {{ width: 15px; height: 15px; color: {p['accent']}; display: block; }}
  .volume-row {{ display: flex; align-items: center; gap: 10px; padding: 8px 2px 4px; }}
  .vol-icon-btn {{ position: relative; width: 18px; height: 18px; cursor: pointer; flex-shrink: 0; }}
  .vol-icon-btn svg {{ width: 15px; height: 15px; color: {p['fg_muted']}; display: block; }}
  .vol-icon-btn .icon-off {{ display: none; }}
  .vol-icon-btn.muted .icon-on {{ display: none; }}
  .vol-icon-btn.muted .icon-off {{ display: block; }}
  .vol-icon-btn.muted svg {{ color: {p['accent']}; }}
  .slider-wrap {{ position: relative; flex: 1; display: flex; align-items: center; }}
  .slider {{
    width: 100%; -webkit-appearance: none; height: 4px; border-radius: 2px;
    background: {p['slider_track']}; outline: none;
  }}
  .slider::-webkit-slider-thumb {{
    -webkit-appearance: none; width: 16px; height: 16px; border-radius: 50%;
    background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.3); cursor: pointer;
  }}
  .vol-bubble {{
    position: absolute; top: -22px; left: 50%; transform: translateX(-50%);
    font-size: 11px; font-weight: 500; background: {p['accent']}; color: {p['fg_on_accent']};
    padding: 1px 7px; border-radius: 8px; opacity: 0; transition: opacity 0.15s;
    pointer-events: none; white-space: nowrap;
  }}
  .vol-num {{
    width: 34px; flex-shrink: 0; background: {p['card_bg']}; color: {p['fg']};
    border: none; border-radius: 6px; padding: 2px 4px; font-size: 11px;
    text-align: center; outline: none;
  }}
  .form-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }}
  .back-btn {{ font-size: 12px; color: {p['fg_muted']}; cursor: pointer; }}
  .back-btn:hover {{ color: {p['fg']}; }}
  .form-title {{ font-size: 13px; font-weight: 600; }}
  .field {{ margin-bottom: 12px; }}
  .field-label {{ font-size: 11px; color: {p['fg_muted']}; margin-bottom: 4px; }}
  .current-hint {{ color: #3ddc97; font-weight: 600; }}
  .text-input, .select-input {{
    width: 100%; box-sizing: border-box; background: {p['card_bg']}; color: {p['fg']};
    border: none; border-radius: 8px; padding: 8px 10px; font-size: 13px; outline: none;
  }}
  .select-input {{ appearance: none; cursor: pointer; }}
  .save-row {{ margin-top: 16px; }}
  .save-btn {{
    width: 100%; background: {p['accent']}; color: {p['fg_on_accent']}; border: none;
    border-radius: 8px; padding: 9px; font-size: 13px; font-weight: 600; cursor: pointer;
  }}
  .save-btn:hover {{ opacity: 0.9; }}
  .error-msg {{ font-size: 11px; color: #e2534a; margin-top: 8px; min-height: 14px; }}
  .ctx-menu {{
    position: fixed; background: {p['card_bg']}; border-radius: 8px; overflow: hidden;
    box-shadow: 0 4px 16px rgba(0,0,0,0.35); z-index: 1000; min-width: 96px;
  }}
  .ctx-item {{ padding: 8px 14px; font-size: 12px; cursor: pointer; color: {p['fg']}; }}
  .ctx-item:hover {{ background: {p['card_hover']}; }}
  .ctx-item.danger {{ color: #e2534a; }}
  .confirm-overlay {{
    position: fixed; inset: 0; background: rgba(0,0,0,0.5);
    display: flex; align-items: center; justify-content: center; z-index: 1100;
  }}
  .confirm-box {{ background: {p['card_bg']}; border-radius: 12px; padding: 16px; width: 230px; }}
  .confirm-msg {{ font-size: 13px; margin-bottom: 14px; text-align: center; color: {p['fg']}; }}
  .confirm-actions {{ display: flex; gap: 8px; }}
  .confirm-btn {{
    flex: 1; border: none; border-radius: 8px; padding: 8px; font-size: 12px; cursor: pointer;
  }}
  .confirm-btn.cancel {{ background: {p['card_hover']}; color: {p['fg']}; }}
  .confirm-btn.danger {{ background: #e2534a; color: white; }}
</style></head>
<body>
  <div id="root">{main_view}</div>

  <script>
    function hswShowAdd() {{
      pywebview.api.get_add_form().then(function(html) {{
        document.getElementById('root').innerHTML = html;
        var nameInput = document.getElementById('add-name');
        if (nameInput) nameInput.focus();
      }});
    }}

    function hswShowMain() {{
      pywebview.api.get_main_view().then(function(html) {{
        document.getElementById('root').innerHTML = html;
      }});
    }}

    function hswSaveProfile() {{
      var name = document.getElementById('add-name').value;
      var icon = document.getElementById('add-icon').value;
      var playbackEl = document.getElementById('add-playback');
      var recordingEl = document.getElementById('add-recording');
      var hotkey = document.getElementById('add-hotkey').value;
      var playbackId = playbackEl ? playbackEl.value : null;
      var recordingId = recordingEl ? recordingEl.value : null;
      var editIdxEl = document.getElementById('add-edit-index');
      var editIdx = editIdxEl && editIdxEl.value !== '' ? editIdxEl.value : null;
      var call = editIdx !== null
        ? pywebview.api.update_profile(editIdx, name, icon, playbackId, recordingId, hotkey)
        : pywebview.api.save_new_profile(name, icon, playbackId, recordingId, hotkey);
      call.then(function(res) {{
        if (!res.ok) {{
          var err = document.getElementById('add-error');
          if (err) err.textContent = res.error || '저장하지 못했어요.';
          return;
        }}
        hswShowMain();
      }});
    }}

    function hswOnProfileContextMenu(e, idx) {{
      e.preventDefault();
      hswShowProfileMenu(e.clientX, e.clientY, idx);
    }}

    function hswShowProfileMenu(x, y, idx) {{
      hswCloseProfileMenu();
      var menu = document.createElement('div');
      menu.id = 'profile-ctx-menu';
      menu.className = 'ctx-menu';
      menu.style.left = x + 'px';
      menu.style.top = y + 'px';
      var editItem = document.createElement('div');
      editItem.className = 'ctx-item';
      editItem.textContent = '수정';
      editItem.onclick = function() {{ hswEditProfile(idx); }};
      var deleteItem = document.createElement('div');
      deleteItem.className = 'ctx-item danger';
      deleteItem.textContent = '삭제';
      deleteItem.onclick = function() {{ hswDeleteProfile(idx); }};
      menu.appendChild(editItem);
      menu.appendChild(deleteItem);
      document.body.appendChild(menu);
      setTimeout(function() {{
        document.addEventListener('click', hswCloseProfileMenu, {{ once: true }});
      }}, 0);
    }}

    function hswCloseProfileMenu() {{
      var menu = document.getElementById('profile-ctx-menu');
      if (menu) menu.remove();
    }}

    function hswEditProfile(idx) {{
      hswCloseProfileMenu();
      pywebview.api.get_edit_form(idx).then(function(html) {{
        document.getElementById('root').innerHTML = html;
        var nameInput = document.getElementById('add-name');
        if (nameInput) nameInput.focus();
      }});
    }}

    function hswDeleteProfile(idx) {{
      hswCloseProfileMenu();
      hswShowConfirmModal('이 프로필을 삭제할까요?', function() {{
        pywebview.api.delete_profile(idx).then(function() {{ hswShowMain(); }});
      }});
    }}

    function hswShowConfirmModal(message, onConfirm) {{
      hswCloseConfirmModal();
      var overlay = document.createElement('div');
      overlay.id = 'confirm-overlay';
      overlay.className = 'confirm-overlay';
      var box = document.createElement('div');
      box.className = 'confirm-box';
      var msg = document.createElement('div');
      msg.className = 'confirm-msg';
      msg.textContent = message;
      var actions = document.createElement('div');
      actions.className = 'confirm-actions';
      var cancelBtn = document.createElement('button');
      cancelBtn.className = 'confirm-btn cancel';
      cancelBtn.textContent = '취소';
      cancelBtn.onclick = hswCloseConfirmModal;
      var okBtn = document.createElement('button');
      okBtn.className = 'confirm-btn danger';
      okBtn.textContent = '삭제';
      okBtn.onclick = function() {{
        hswCloseConfirmModal();
        onConfirm();
      }};
      actions.appendChild(cancelBtn);
      actions.appendChild(okBtn);
      box.appendChild(msg);
      box.appendChild(actions);
      overlay.appendChild(box);
      document.body.appendChild(overlay);
    }}

    function hswCloseConfirmModal() {{
      var overlay = document.getElementById('confirm-overlay');
      if (overlay) overlay.remove();
    }}

    var hswClosed = false;
    window.addEventListener('blur', function() {{
      if (hswClosed) return;
      hswClosed = true;
      pywebview.api.close();
    }});

    function hswVolInput(el, deviceId, bubbleId, numId) {{
      pywebview.api.set_volume(deviceId, el.value);
      var bubble = document.getElementById(bubbleId);
      if (bubble) {{
        bubble.textContent = el.value;
        bubble.style.opacity = '1';
        var pct = (el.value - el.min) / (el.max - el.min);
        var offset = pct * (el.offsetWidth - 16) + 8;
        bubble.style.left = offset + 'px';
      }}
      var num = document.getElementById(numId);
      if (num) num.value = el.value;
    }}

    function hswVolEnd(bubbleId) {{
      var bubble = document.getElementById(bubbleId);
      if (!bubble) return;
      setTimeout(function() {{ bubble.style.opacity = '0'; }}, 500);
    }}

    function hswVolNumInput(el, deviceId, sliderId) {{
      var val = Math.max(0, Math.min(100, parseInt(el.value, 10) || 0));
      el.value = val;
      var slider = document.getElementById(sliderId);
      if (slider) slider.value = val;
      pywebview.api.set_volume(deviceId, val);
    }}

    function hswToggleMute(deviceId, key) {{
      pywebview.api.toggle_mute(deviceId).then(function(isMuted) {{
        var el = document.getElementById('vol_icon_' + key);
        if (!el) return;
        if (isMuted) {{ el.classList.add('muted'); }} else {{ el.classList.remove('muted'); }}
      }});
    }}

    var hswIdleTimer = null;
    function hswResetIdleTimer() {{
      if (hswIdleTimer) clearTimeout(hswIdleTimer);
      hswIdleTimer = setTimeout(function() {{
        if (hswClosed) return;
        hswClosed = true;
        pywebview.api.close();
      }}, 4500);
    }}
    ['mousemove', 'mousedown', 'keydown', 'input', 'wheel'].forEach(function(evt) {{
      window.addEventListener(evt, hswResetIdleTimer);
    }});
    hswResetIdleTimer();
  </script>
</body></html>"""


def _compute_geometry(app):
    n_profiles = len(config_manager.load_profiles()) + 1
    n_rows = len(app.playback_devices) + len(app.recording_devices)
    height = 150 + ((n_profiles - 1) // 3 + 1) * 86 + n_rows * 42 + 110
    height = min(max(height, 420), 820)
    width = 332

    screen_w = app.screen_width
    screen_h = app.screen_height
    x = screen_w - width - 12
    y = screen_h - height - 16
    return width, height, x, y


_keepalive_window = None
_current_popup = {"window": None}


def init_window(app):
    """
    프로그램 시작 시 한 번만 호출 (진짜 메인 스레드에서). pywebview 이벤트 루프를
    계속 살려두기 위한 보이지 않는 keep-alive 창을 만든다. 실제 팝업은
    show_tray_popup_web()에서 매번 새로 만들고 버린다.
    """
    global _keepalive_window
    _keepalive_window = webview.create_window(
        "HSSwitch (background)", html="<html></html>", width=1, height=1, hidden=True,
    )


def run_event_loop():
    """pywebview 이벤트 루프 시작 (블로킹). 반드시 실제 메인 스레드에서 호출해야 한다."""
    webview.start()


# pywebview 팝업 창의 내부 타이틀. 프레임리스라 화면에 보이진 않지만,
# 메인 tkinter 창(APP_TITLE="HSSwitch")과 같은 문자열을 쓰면 FindWindowW가
# 숨겨진 메인 창을 잘못 집을 수 있어서 반드시 고유한 값을 써야 한다.
POPUP_WINDOW_TITLE = "HSSwitchPopup"

# 백그라운드 스레드(트레이 아이콘 클릭 콜백)에서 SetForegroundWindow를 호출하면
# Windows가 기본적으로 막기 때문에, ALT 키를 살짝 눌렀다 떼는 척해서 우회한다.
# (포그라운드 잠금을 우회하는 잘 알려진 트릭)
VK_MENU = 0x12
KEYEVENTF_KEYUP = 0x0002
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
HWND_TOPMOST = -1


def _find_popup_hwnd():
    return ctypes.windll.user32.FindWindowW(None, POPUP_WINDOW_TITLE)


def _apply_rounded_corners(width, height):
    """Windows GDI를 직접 호출해서 창 외곽을 실제로 둥글게 잘라낸다."""
    try:
        hwnd = _find_popup_hwnd()
        if not hwnd:
            return
        region = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, width + 1, height + 1, 20, 20)
        ctypes.windll.user32.SetWindowRgn(hwnd, region, True)
    except Exception:
        pass


def _force_foreground():
    """
    다른 always-on-top 창(예: 브라우저 PiP)에 팝업이 가려지거나, 백그라운드
    스레드에서 만든 창이라 포커스를 못 받는 경우를 방지하기 위해 강제로
    맨 앞으로 올리고 포커스를 가져온다.
    """
    try:
        hwnd = _find_popup_hwnd()
        if not hwnd:
            return
        user32 = ctypes.windll.user32
        # topmost 재적용 (다른 topmost 창에 밀린 z-order 복구)
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        user32.BringWindowToTop(hwnd)
        # 포그라운드 잠금 우회
        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.SetForegroundWindow(hwnd)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    except Exception:
        pass


def show_tray_popup_web(app):
    """트레이 클릭 시 호출. 매번 새 팝업 창을 만들어 보여주고, 닫힐 때 완전히 폐기한다."""
    old = _current_popup.get("window")
    if old is not None:
        try:
            old.destroy()
        except Exception:
            pass
        _current_popup["window"] = None

    width, height, x, y = _compute_geometry(app)
    palette = theme_manager.get_palette(theme_manager.resolve_theme())
    holder = {}
    api = Api(app, holder)

    window = webview.create_window(
        POPUP_WINDOW_TITLE,
        html=_build_html(app),
        width=width,
        height=height,
        x=x,
        y=y,
        frameless=True,
        easy_drag=False,
        on_top=True,
        js_api=api,
        background_color=palette["popup_bg"],
    )
    holder["window"] = window
    _current_popup["window"] = window

    def _on_loaded():
        _apply_rounded_corners(width, height)
        _force_foreground()

    window.events.loaded += _on_loaded


def shutdown():
    """프로그램 종료 시 호출. 열려 있는 창들을 정리하고 이벤트 루프를 끝낸다."""
    popup = _current_popup.get("window")
    if popup is not None:
        try:
            popup.destroy()
        except Exception:
            pass
    if _keepalive_window is not None:
        try:
            _keepalive_window.destroy()
        except Exception:
            pass
