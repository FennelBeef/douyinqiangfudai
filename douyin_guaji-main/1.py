import subprocess
import re
from typing import List, Dict, Optional


def get_adb_devices_with_status():
    """获取所有ADB设备及其状态"""
    try:
        result = subprocess.run(
            ['adb', 'devices'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=10
        )

        if result.returncode != 0:
            print(f"ADB命令执行失败: {result.stderr}")
            return []

        devices = []
        lines = result.stdout.strip().split('\n')

        # 解析设备列表（包含状态）
        for line in lines[1:]:  # 跳过第一行标题
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    device_id = parts[0]
                    status = parts[1]
                    devices.append({'id': device_id, 'status': status})

        return devices

    except Exception as e:
        print(f"获取设备列表失败: {e}")
        return []


def analyze_device(device_info: Dict) -> Dict:
    """分析设备类型和信息"""
    device_id = device_info['id']
    status = device_info['status']

    if device_id.startswith('adb-'):
        # mDNS无线设备
        parts = device_id.split('.')
        info = {
            'type': 'mdns_wireless',
            'full_id': device_id,
            'base_id': parts[0],
            'service_type': parts[1] if len(parts) > 1 else '',
            'protocol': parts[2] if len(parts) > 2 else '',
            'is_encrypted': '_tls-connect' in device_id,
            'is_wireless': True,
            'status': status
        }
        return info
    elif ':' in device_id:
        # 传统无线设备（IP:端口）
        return {
            'type': 'wireless',
            'id': device_id,
            'is_wireless': True,
            'status': status
        }
    else:
        # USB设备或序列号
        return {
            'type': 'usb',
            'id': device_id,
            'is_wireless': False,
            'status': status
        }


def display_devices(devices: List[Dict]):
    """显示设备列表"""
    print("📱 连接的设备:")
    print("-" * 60)

    online_devices = []
    offline_devices = []

    for device in devices:
        if device['status'] == 'device':
            online_devices.append(device)
        else:
            offline_devices.append(device)

    # 显示在线设备
    if online_devices:
        print("✅ 在线设备:")
        for i, device in enumerate(online_devices, 1):
            info = analyze_device(device)
            status_icon = "🔒" if info.get('is_encrypted', False) else "📶"
            if info['type'] == 'mdns_wireless':
                print(f"   {i}. {status_icon} {device['id']} (mDNS无线设备)")
            elif info['type'] == 'wireless':
                print(f"   {i}. 📶 {device['id']} (无线设备)")
            else:
                print(f"   {i}. 🔌 {device['id']} (USB设备)")

    # 显示离线设备
    if offline_devices:
        print("\n❌ 离线设备:")
        for i, device in enumerate(offline_devices, len(online_devices) + 1):
            info = analyze_device(device)
            if info['type'] == 'mdns_wireless':
                print(f"   {i}. ⚠️  {device['id']} (mDNS无线设备 - 离线)")
            elif info['type'] == 'wireless':
                print(f"   {i}. ⚠️  {device['id']} (无线设备 - 离线)")
            else:
                print(f"   {i}. ⚠️  {device['id']} (USB设备 - 离线)")

    print("-" * 60)
    return online_devices, offline_devices


def select_online_device(online_devices: List[Dict]) -> Optional[Dict]:
    """选择在线设备"""
    if not online_devices:
        print("没有在线的设备可用")
        return None

    if len(online_devices) == 1:
        print(f"自动选择唯一在线设备: {online_devices[0]['id']}")
        return online_devices[0]

    try:
        choice = int(input("请选择在线设备编号: "))
        if 1 <= choice <= len(online_devices):
            return online_devices[choice - 1]
        else:
            print("无效的选择")
            return None
    except ValueError:
        print("请输入数字")
        return None


def reconnect_offline_device(device_info: Dict) -> bool:
    """尝试重新连接离线设备"""
    device_id = device_info['id']
    print(f"尝试重新连接设备: {device_id}")

    try:
        # 先断开连接
        subprocess.run(
            ['adb', 'disconnect', device_id],
            capture_output=True,
            timeout=5
        )

        # 如果是无线设备，尝试重新连接
        if ':' in device_id or device_id.startswith('adb-'):
            result = subprocess.run(
                ['adb', 'connect', device_id],
                capture_output=True,
                text=True,
                timeout=10
            )
            if 'connected' in result.stdout:
                print(f"✅ 重新连接成功: {device_id}")
                return True
            else:
                print(f"❌ 重新连接失败: {result.stderr}")
                return False
        else:
            print("请检查USB连接或设备状态")
            return False

    except Exception as e:
        print(f"重新连接过程中出错: {e}")
        return False


# 主函数
def main():
    """主设备选择函数"""
    devices = get_adb_devices_with_status()

    if not devices:
        print("没有找到任何设备")
        return None

    online_devices, offline_devices = display_devices(devices)

    # 如果没有在线设备，询问是否尝试重新连接
    if not online_devices and offline_devices:
        print("所有设备都处于离线状态")
        choice = input("是否尝试重新连接离线设备？(y/n): ")
        if choice.lower() == 'y':
            for device in offline_devices:
                if reconnect_offline_device(device):
                    # 重新检查设备状态
                    devices = get_adb_devices_with_status()
                    online_devices, _ = display_devices(devices)
                    if online_devices:
                        break

    # 选择在线设备
    selected_device = select_online_device(online_devices)

    if selected_device:
        device_info = analyze_device(selected_device)
        print(f"\n🎯 选择的设备:")
        print(f"   ID: {selected_device['id']}")
        print(f"   类型: {device_info['type']}")
        print(f"   状态: {device_info['status']}")
        print(f"   无线连接: {device_info['is_wireless']}")
        if device_info.get('is_encrypted', False):
            print(f"   加密连接: ✅")

        return selected_device['id']

    return None


# 使用示例
if __name__ == "__main__":
    selected_device_id = main()
    if selected_device_id:
        print(f"\n✅ 已选择设备: {selected_device_id}")
        # 这里可以继续执行其他ADB命令
    else:
        print("\n❌ 没有选择设备")
    string = subprocess.Popen('adb devices', shell=True, stdout=subprocess.PIPE)
    totalstring = string.stdout.read()
    totalstring = totalstring.decode('UTF-8')
    # print(totalstring)
    # pattern = r'(\b(?:[0-9]{1,3}(?:\.[0-9]{1,3}){3}(?::[0-9]+)?|[A-Za-z0-9]{8,})\b)\s*device\b'
    pattern = r'([^\s]+)\s+device\b'
    devicelist = re.findall(pattern, totalstring)
    # devicelist = re.compile(r'(\w*)\s*device\b').findall(totalstring)
    devicenum = len(devicelist)
    print(devicenum)