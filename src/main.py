import winreg
import subprocess


MONITOR_CLASS_GUID = "{4d36e96e-e325-11ce-bfc1-08002be10318}"


def enumerate_monitors():
    monitors = []
    base_key = r"SYSTEM\CurrentControlSet\Enum\DISPLAY"

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_key) as root:
            model_index = 0

            while True:
                try:
                    model_name = winreg.EnumKey(root, model_index)
                    model_index += 1
                except OSError:
                    break

                model_path = f"{base_key}\\{model_name}"

                try:
                    with winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE, model_path
                    ) as model_key:

                        instance_index = 0

                        while True:
                            try:
                                instance_name = winreg.EnumKey(
                                    model_key, instance_index
                                )
                                instance_index += 1
                            except OSError:
                                break

                            instance_path = (
                                f"{model_path}\\{instance_name}"
                            )

                            instance_id = (
                                f"DISPLAY\\{model_name}\\{instance_name}"
                            )

                            try:
                                with winreg.OpenKey(
                                    winreg.HKEY_LOCAL_MACHINE,
                                    instance_path
                                ) as inst_key:

                                    try:
                                        class_guid, _ = winreg.QueryValueEx(
                                            inst_key, "ClassGUID"
                                        )
                                    except OSError:
                                        continue

                                    if class_guid.casefold() != (
                                        MONITOR_CLASS_GUID.casefold()
                                    ):
                                        continue

                                    name = model_name

                                    for value_name in (
                                        "FriendlyName",
                                        "DeviceDesc",
                                    ):
                                        try:
                                            value, _ = winreg.QueryValueEx(
                                                inst_key, value_name
                                            )

                                            if value:
                                                name = value.split(";")[-1].strip()
                                                break

                                        except OSError:
                                            continue

                                    monitors.append({
                                        "name": name,
                                        "instance_id": instance_id,
                                    })

                            except OSError:
                                continue

                except OSError:
                    continue

    except OSError:
        pass

    return monitors


def disable_monitors(instance_ids):
    results = []

    for iid in instance_ids:
        try:
            result = subprocess.run(
                ["pnputil.exe", "/disable-device", iid],
                creationflags=subprocess.CREATE_NO_WINDOW,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            results.append({
                "instance_id": iid,
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "output": result.stdout.strip(),
                "error": result.stderr.strip(),
            })

        except subprocess.TimeoutExpired:
            results.append({
                "instance_id": iid,
                "success": False,
                "error": "Operation timed out",
            })

        except OSError as exc:
            results.append({
                "instance_id": iid,
                "success": False,
                "error": str(exc),
            })

    return results



if __name__ == "__main__":
    print("=" * 55)
    print("          monitor disabler (vibecoded)")
    print("=" * 55)

    monitors = enumerate_monitors()

    if not monitors:
        print("\n[!] No monitor devices found.")
        input("\nPress Enter to exit...")
        raise SystemExit(0)

    print(f"\n[+] Found {len(monitors)} monitor device(s):\n")

    for index, monitor in enumerate(monitors, 1):
        print(f"[{index}] {monitor['name']}")
        print(f"    ID: {monitor['instance_id']}")

    print("\n" + "=" * 55)
    print("[*] Starting monitor disable operations...")
    print("=" * 55)

    results = disable_monitors(
        [m["instance_id"] for m in monitors]
    )

    success = 0
    failed = 0

    for index, result in enumerate(results, 1):
        if result["success"]:
            success += 1
            #print(f"[+] Monitor {index}: DISABLED")
        else:
            failed += 1
            #print(f"[-] Monitor {index}: FAILED")
            #print(f"    Error: {result.get('error', result.get('output', 'Unknown error'))}")

    if success == 1:
        print("done")
    else:
        print("fail")

    input("\nPress Enter to exit...")
