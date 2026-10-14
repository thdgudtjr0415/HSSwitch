"""
재생/녹음 장치 목록과 현재 기본 장치를 조회한다(pycaw).

tkinter 스레드와 pywebview JS 브리지 콜백 스레드(트레이 팝업) 어디서든 불릴 수 있으므로,
volume_control.py처럼 매 호출마다 스스로 COM을 초기화한다(이미 초기화된 스레드에서 또 불러도 안전).
"""

import warnings
from dataclasses import dataclass

import comtypes
from pycaw.constants import DEVICE_STATE, EDataFlow
from pycaw.pycaw import AudioUtilities


@dataclass
class DeviceInfo:
    id: str
    name: str


def _get_devices(data_flow: int) -> list[DeviceInfo]:
    # 부팅 직후(--startup)에는 오디오 서비스나 무선 동글이 아직 준비되지 않아 GetAllDevices가 COM 예외를
    # 던질 수 있다. 예외가 새면 앱 초기화 스레드가 죽어 아무 반응 없이 실행 안 되므로 빈 목록을 돌려준다.
    comtypes.CoInitialize()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)  # 일부 특수 장치의 COMError 경고
            devices = AudioUtilities.GetAllDevices(
                data_flow=data_flow, device_state=DEVICE_STATE.ACTIVE.value
            )
    except Exception:
        return []

    result = []
    for d in devices:
        try:
            result.append(DeviceInfo(id=d.id, name=d.FriendlyName))
        except Exception:
            continue
    return result


def get_playback_devices() -> list[DeviceInfo]:
    """스피커, 헤드셋 등 출력(재생) 장치 목록"""
    return _get_devices(EDataFlow.eRender.value)


def get_recording_devices() -> list[DeviceInfo]:
    """마이크 등 입력(녹음) 장치 목록"""
    return _get_devices(EDataFlow.eCapture.value)


def get_default_playback_id() -> str | None:
    comtypes.CoInitialize()
    try:
        return AudioUtilities.GetSpeakers().id
    except Exception:
        return None


def get_default_recording_id() -> str | None:
    comtypes.CoInitialize()
    try:
        device_enumerator = AudioUtilities.GetDeviceEnumerator()
        # eCapture=1, eMultimedia=1
        endpoint = device_enumerator.GetDefaultAudioEndpoint(1, 1)
        return AudioUtilities.CreateDevice(endpoint).id
    except Exception:
        return None
