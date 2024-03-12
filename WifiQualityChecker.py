import re
import subprocess
import sys


def WifiQualityChecker(interface="wlan0"):
    """Wifi quality and signal level for Linux or Raspberry PI"""

    # Signal Strengt Values in dBm
    Perfect = 30  # level 6 - perfect signal strenght
    Excellent = 50  # level 5 - excellent signal strenght
    Good = 60  # level 4 - good reliable signal
    Minimal = 67  # level 3 - minimum for voice and non HD video
    Poor = 70  # level 2 - only for light browsing and email
    TooLow = 80  # level 1 - unstable or no connection

    # Regular expression pattern to extract Signal level
    pattern1 = r"Link Quality=(-?\d+)/"

    # Regular expression pattern to extract Signal Quality
    pattern2 = r"Signal level=(-?\d+)\sdBm"

    try:
        result = subprocess.run(["iwconfig", interface], stdout=subprocess.PIPE)
        out = result.stdout.decode("utf-8")
        # print("résultat command: ", out)

        # Search for the pattern1 in the string
        match1 = re.search(pattern1, out)
        if match1:
            link_quality = int(match1.group(1))
        else:
            print("Link Quality not found in the string.")

        # Search for the pattern2 in the string
        match2 = re.search(pattern2, out)
        if match2:
            signal_level = int(match2.group(1))
        else:
            print("Signal level not found in the string.")

        if abs(signal_level) > Perfect and abs(signal_level) <= Excellent:
            Wifi_Quality = "Perfect"
        if abs(signal_level) > Excellent and abs(signal_level) <= Good:
            Wifi_Quality = "Excellent"
        if abs(signal_level) > Good and abs(signal_level) <= Minimal:
            Wifi_Quality = "Good "
        if abs(signal_level) > Minimal and abs(signal_level) <= Poor:
            Wifi_Quality = "Minimal"
        if abs(signal_level) > Poor and abs(signal_level) <= TooLow:
            Wifi_Quality = "Poor"
        if abs(signal_level) > TooLow:
            Wifi_Quality = "Too Low"

        return Wifi_Quality, signal_level, link_quality

    except:
        print("Error system :", sys.exc_info()[0])


if __name__:

    Wifi_Quality, Signal_level, Link_Quality = WifiQualityChecker("wlan0")
    print("Wifi Quality Checker for Raspberry PI 4")
    print("Wifi Quality : ", Wifi_Quality)
    print("Signal level : ", Signal_level, "dBm")
    print("Link Quality : ", Link_Quality, "/70")
