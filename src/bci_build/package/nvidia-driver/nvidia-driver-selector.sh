#!/bin/bash

# Determines whether to use 'open' or 'proprietary' kernel modules based on detected NVIDIA GPUs.

JSON_PATH="${1:-${JSON_PATH:-/usr/share/nvidia-driver-assistant/supported-gpus/supported-gpus.json}}"


if [ -z "$JSON_PATH" ] || [ ! -f "$JSON_PATH" ]; then
    echo "Error: supported-gpus.json not found. Set JSON_PATH environment variable or pass it as an argument." >&2
    exit 1
fi

# Check for jq
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed." >&2
    exit 1
fi

DETECTED_IDS=()

# Scan sysfs for NVIDIA GPUs (Vendor 0x10de, Class 0x03xxxx)
SYSFS_PATH="${SYSFS_PATH:-/sys/bus/pci/devices}"

# Using nullglob to handle case where no devices exist
shopt -s nullglob
for dev in "$SYSFS_PATH"/*; do
    if [ -f "$dev/vendor" ]; then
        vendor=$(cat "$dev/vendor")
        if [ "$vendor" == "0x10de" ]; then
            class=$(cat "$dev/class")
            # Class 0x03... is Display Controller (VGA compatible or 3D)
            if [[ "$class" == 0x03* ]]; then
                device=$(cat "$dev/device")
                # Device ID is usually lowercase in sysfs (e.g. 0x1234)
                # We need to normalize this for consistency
                DETECTED_IDS+=("$device")
            fi
        fi
    fi
done
shopt -u nullglob

if [ ${#DETECTED_IDS[@]} -eq 0 ]; then
    echo "No NVIDIA GPUs detected." >&2
    exit 1
fi

# Build JSON array of detected IDs (normalized to 0xXXXX uppercase to match supported-gpus.json)
DETECTED_JSON="["
first=true
for id in "${DETECTED_IDS[@]}"; do
    # Normalize: 0x + uppercase hex
    normalized_id=$(echo "$id" | awk '{print "0x" toupper(substr($0, 3))}')
    if [ "$first" = true ]; then
        DETECTED_JSON+="\"$normalized_id\""
        first=false
    else
        DETECTED_JSON+=",\"$normalized_id\""
    fi
done
DETECTED_JSON+="]"

# Use jq to implement the decision logic
# Using single line to avoid any potential here-doc/newline issues in this environment
# Mapping logic:
# - kernelopen and NOT gsp_proprietary_supported -> "open_required" (open_only)
# - kernelopen and gsp_proprietary_supported -> "gsp_proprietary_supported" (hybrid)
# - NOT kernelopen -> "proprietary_required" (closed_only)
# - Unknown -> "open_required" (open_only)
RESULT=$(jq -n -r --argjson devices "$DETECTED_JSON" --slurpfile data "$JSON_PATH" '
  ($data[0].chips) as $chips |
  $devices |
  map(. as $id |
    ($chips | map(select(.devid == $id)) | .[-1]) as $chip |
    if $chip then
      if ($chip.features | index("kernelopen")) then
        if ($chip.features | index("gsp_proprietary_supported")) then
          "hybrid"
        else
          "open_only"
        end
      else
        "closed_only"
      end
    else
      "open_only"
    end
  ) as $hints |
  if ($hints | all(. == "open_only" or . == "hybrid")) then
    "open"
  elif ($hints | all(. == "closed_only")) then
    "proprietary"
  elif ($hints | any(. == "open_only")) then
    "open"
  elif ($hints | any(. == "closed_only")) then
    "proprietary"
  else
    "open"
  end')

if [ -z "$RESULT" ]; then
    echo "Error: Failed to determine driver." >&2
    exit 1
fi

echo "$RESULT"
exit 0
