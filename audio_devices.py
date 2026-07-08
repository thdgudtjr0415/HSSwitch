"""
Windows에 연결된 재생(스피커/헤드셋) 장치와 녹음(마이크) 장치 목록을
조회하는 모듈. pycaw의 공식 문서 예제 패턴을 그대로 따른다.
"""

import warnings
from dataclasses import dataclass

from pycaw.constants import DEVICE_STATE, EDataFlow
from pycaw.pycaw import AudioUtilities


@dataclass
class DeviceInfo:
    id: str
    name: str


def _get_devices(data_flow: int) -> list[DeviceInfo]:
    with warnings.catch_warnings():
        # 일부 비활성/특수 장치에서 COMError 경고가 뜨는데 무시해도 무방
        warnings.simplefilter("ignore", UserWarning)
        devices = AudioUtilities.GetAllDevices(
            data_flow=data_flow, device_state=DEVICE_STATE.ACTIVE.value
        )
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
    try:
        return AudioUtilities.GetSpeakers().id
    except Exception:
        return None


def get_default_recording_id() -> str | None:
    try:
        device_enumerator = AudioUtilities.GetDeviceEnumerator()
        # eCapture=1, eMultimedia=1
        endpoint = device_enumerator.GetDefaultAudioEndpoint(1, 1)
        return AudioUtilities.CreateDevice(endpoint).id
    except Exception:
        return None
