"""
Windows의 문서화되지 않은 IPolicyConfig COM 인터페이스를 이용해
기본 재생/녹음 장치를 실제로 변경하는 모듈.

pycaw만으로는 '조회'는 되지만 '기본 장치 변경'은 안 되기 때문에
comtypes로 저수준 COM 인터페이스를 직접 호출한다.
"""

from ctypes import HRESULT, c_int, c_void_p, c_wchar_p

import comtypes
from comtypes import GUID, COMMETHOD, IUnknown, CoCreateInstance, CLSCTX_ALL

CLSID_PolicyConfigClient = GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}")
IID_IPolicyConfig = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")

# eConsole=0, eMultimedia=1, eCommunications=2
ERole = c_int


class IPolicyConfig(IUnknown):
    _case_insensitive_ = True
    _iid_ = IID_IPolicyConfig
    _methods_ = [
        COMMETHOD([], HRESULT, "GetMixFormat",
                  (["in"], c_wchar_p, "pszDeviceName"),
                  (["out"], c_void_p, "ppFormat")),
        COMMETHOD([], HRESULT, "GetDeviceFormat",
                  (["in"], c_wchar_p, "pszDeviceName"),
                  (["in"], c_int, "bDefault"),
                  (["out"], c_void_p, "ppFormat")),
        COMMETHOD([], HRESULT, "ResetDeviceFormat",
                  (["in"], c_wchar_p, "pszDeviceName")),
        COMMETHOD([], HRESULT, "SetDeviceFormat",
                  (["in"], c_wchar_p, "pszDeviceName"),
                  (["in"], c_void_p, "pEndpointFormat"),
                  (["in"], c_void_p, "pMixFormat")),
        COMMETHOD([], HRESULT, "GetProcessingPeriod",
                  (["in"], c_wchar_p, "pszDeviceName"),
                  (["in"], c_int, "bDefault"),
                  (["out"], c_void_p, "pmftDefaultPeriod"),
                  (["out"], c_void_p, "pmftMinimumPeriod")),
        COMMETHOD([], HRESULT, "SetProcessingPeriod",
                  (["in"], c_wchar_p, "pszDeviceName"),
                  (["in"], c_void_p, "pmftPeriod")),
        COMMETHOD([], HRESULT, "GetShareMode",
                  (["in"], c_wchar_p, "pszDeviceName"),
                  (["out"], c_void_p, "pMode")),
        COMMETHOD([], HRESULT, "SetShareMode",
                  (["in"], c_wchar_p, "pszDeviceName"),
                  (["in"], c_void_p, "mode")),
        COMMETHOD([], HRESULT, "GetPropertyValue",
                  (["in"], c_wchar_p, "pszDeviceName"),
                  (["in"], c_int, "bFxStore"),
                  (["in"], c_void_p, "key"),
                  (["out"], c_void_p, "pv")),
        COMMETHOD([], HRESULT, "SetPropertyValue",
                  (["in"], c_wchar_p, "pszDeviceName"),
                  (["in"], c_int, "bFxStore"),
                  (["in"], c_void_p, "key"),
                  (["in"], c_void_p, "pv")),
        COMMETHOD([], HRESULT, "SetDefaultEndpoint",
                  (["in"], c_wchar_p, "pszDeviceName"),
                  (["in"], ERole, "eRole")),
        COMMETHOD([], HRESULT, "SetEndpointVisibility",
                  (["in"], c_wchar_p, "pszDeviceName"),
                  (["in"], c_int, "bVisible")),
    ]


def set_default_device(device_id: str):
    """
    device_id: pycaw device.id (엔드포인트 ID 문자열)
    콘솔/멀티미디어/통신 세 가지 role 모두에 대해 기본 장치로 설정한다.
    (역할별로 따로 설정하지 않으면 일부 앱에서만 바뀌는 문제가 생긴다)
    """
    comtypes.CoInitialize()
    try:
        policy_config = CoCreateInstance(
            CLSID_PolicyConfigClient,
            IPolicyConfig,
            CLSCTX_ALL,
        )
        for role in (0, 1, 2):  # eConsole, eMultimedia, eCommunications
            policy_config.SetDefaultEndpoint(device_id, role)
    finally:
        comtypes.CoUninitialize()
