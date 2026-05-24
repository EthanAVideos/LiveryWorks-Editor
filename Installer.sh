#!/bin/bash

#Author: Ethan. Created: 5/19/26. Updated: 5/20/26. VERSION: 2.3.2 Build 8

# Terminal setup
setup_terminal() {
    old_stty=$(stty -g)
    stty -echo -icanon min 1 time 0
    printf '\033[?25l'
}

restore_terminal() {
    stty "$old_stty"
    printf '\033[?25h'
    printf '\033[2J\033[H'
}

# Added for installing addons
safe_read_input() {
    local prompt="$1"
    local var_name="$2"

    # Save current terminal state and restore to normal for input
    local saved_stty=$(stty -g)
    stty "$old_stty"
    printf '\033[?25h'  # Show cursor

    # Read user input
    read -p "$prompt" $var_name

    # Go back to raw mode
    stty -echo -icanon min 1 time 0
    printf '\033[?25l'  # Hide cursor again
}
# Added for installing addons

# Get terminal dimensions
get_terminal_size() {
    TERM_ROWS=$(tput lines 2>/dev/null || echo 24)
    TERM_COLS=$(tput cols 2>/dev/null || echo 80)
}

# Define colors
BOLD="\033[1m"
DIM="\033[2m"
RESET="\033[0m"
WHITE="\033[37m"
BOLD_WHITE="\033[1;37m"
BG_BLUE="\033[34m"
GREEN="\033[32m"
YELLOW="\033[33m"
CYAN="\033[36m"
MAGENTA="\033[35m"
BLUE="\033[34m"
RED="\033[31m"
BOLD_GREEN="\033[1;32m"
BOLD_YELLOW="\033[1;33m"
BOLD_CYAN="\033[1;36m"
BOLD_MAGENTA="\033[1;35m"
DARK_BLUE="\033[1;34m"
BOLD_RED="\033[1;31m"

#Error and warning echo colors.
GREEN='\e[0;32m'
RED_BOLD='\e[1;31m'
YELLOW_B='\e[1;33m'
RESET='\e[0m'

# 5 Sec. Progress bar.
DURATION=5
BAR_LENGTH=50

# Installation script
TARGET_DIR="$HOME/Documents/LWE"

#Downloadables
ZIP_URL="https://github.com/EthanAVideos/LiveryWorks-Editor/releases/download/1.6.9.B8/LiveryWorks_Editor1698.zip"
TEMP_ZIP="/tmp/LiveryWorks_Editor1698.zip"

# Clear and set background for entire row
fill_row() {
    local row=$1
    local col=$2
    local width=$3

    echo -ne "\033[${row};${col}H"
    echo -ne "${BG_BLUE}"
    printf "%${width}s" ""
    echo -ne "${RESET}"
}

# Draw centered box
draw_box() {
    local start_row=$1
    local start_col=$2
    local width=$3
    local height=$4

    # Top border
    echo -ne "\033[${start_row};${start_col}H${GREEN}╔"
    for ((i=0; i<width-2; i++)); do echo -ne "═"; done
    echo -ne "╗${RESET}"

    # Middle
    for ((i=1; i<height-1; i++)); do
        fill_row $((start_row+i)) $start_col $width
        echo -ne "\033[$((start_row+i));${start_col}H${GREEN}║"
        echo -ne "\033[$((start_row+i));$((start_col+width-1))H║${RESET}"
    done

    # Bottom
    echo -ne "\033[$((start_row+height-1));${start_col}H${GREEN}╚"
    for ((i=0; i<width-2; i++)); do echo -ne "═"; done
    echo -ne "╝${RESET}"
}

# Show message screen
show_message() {
    local title=$1
    shift
    local messages=("$@")

    get_terminal_size
    local width=50
    local height=$((${#messages[@]} + 7))
    local start_row=$(( (TERM_ROWS - height) / 2 ))
    local start_col=$(( (TERM_COLS - width) / 2 ))

    echo -ne "\033[2J\033[H"
    draw_box $start_row $start_col $width $height

    # Title
    local title_row=$((start_row + 3))
    local title_col=$((start_col + (width - ${#title}) / 2))
    echo -ne "\033[${title_row};${title_col}H${BG_BLUE}${BOLD}${WHITE}${title}${RESET}"

    # Messages
    for i in "${!messages[@]}"; do
        local msg_row=$((start_row + 4 + i))
        local msg_col=$((start_col + 4))
        echo -ne "\033[${msg_row};${msg_col}H${BG_BLUE}${WHITE}${messages[$i]}${RESET}"
    done

    # Footer
    local footer_row=$((start_row + height - 2))
    echo -ne "\033[${footer_row};$((start_col + (width - 30) / 2))H${BG_BLUE}${WHITE}Press Enter to continue...${RESET}"

    read
}

# Read key with proper arrow key handling using dd
get_key() {
    # Read first byte
    local key=$(dd bs=1 count=1 2>/dev/null)

    # Check if it's an escape character
    if [ "$key" = $'\033' ]; then
        # Read next byte (should be '[')
        local second=$(dd bs=1 count=1 2>/dev/null)
        if [ "$second" = "[" ]; then
            # Read arrow key identifier
            local third=$(dd bs=1 count=1 2>/dev/null)
            case "$third" in
                A) echo "UP" ;;
                B) echo "DOWN" ;;
                C) echo "RIGHT" ;;
                D) echo "LEFT" ;;
                *) echo "UNKNOWN" ;;
            esac
        else
            echo "ESC"
        fi
    elif [ -z "$key" ]; then
        echo "ENTER"
    else
        echo "$key"
    fi
}

# Main menu
show_menu() {
    local items=("$@")
    local selected=0
    local total=${#items[@]}
    local width=48
    local height=$((total + 9))

    local item_colors=("$BOLD_GREEN" "$BOLD_GREEN" "$BOLD_YELLOW" "$BOLD_RED")

    while true; do
        get_terminal_size
        local start_row=$(( (TERM_ROWS - height) / 2 ))
        local start_col=$(( (TERM_COLS - width) / 2 ))

        echo -ne "\033[2J\033[H"
        draw_box $start_row $start_col $width $height

        # Title
        local title_row=$((start_row + 1))
        echo -ne "\033[${title_row};$((start_col + 9))H${GREEN}${GREEN}╔══════════════════════╗${RESET}"
        echo -ne "\033[$((title_row+1));$((start_col+9))H${GREEN}${GREEN}║  INSTALLER           ║${RESET}"
        echo -ne "\033[$((title_row+2));$((start_col+9))H${GREEN}${GREEN}║  EAVCFM: 2.3.2.B8    ║${RESET}"
        echo -ne "\033[$((title_row+3));$((start_col+9))H${GREEN}${GREEN}╚══════════════════════╝${RESET}"

        # Menu items
        for i in "${!items[@]}"; do
            local item_row=$((start_row + 6 + i))
            echo -ne "\033[${item_row};${start_col}H${GREEN}"
            printf "║%$((width-2))s║" ""

            local color="${item_colors[$((i % ${#item_colors[@]}))]}"
            if [ $i -eq $selected ]; then
                echo -ne "\033[${item_row};$((start_col+4))H${BG_BLUE}${color}▸ ${items[$i]} ◂${RESET}"
            else
                echo -ne "\033[${item_row};$((start_col+4))H${BG_BLUE}${WHITE}  ${items[$i]}${RESET}"
            fi
        done

        # Footer
        local footer_row=$((start_row + height - 2))
        echo -ne "\033[${footer_row};${start_col}H${GREEN}${WHITE}"
        printf "║%$((width-2))s║" "  ↑↓ Navigate    ↵ Select    q Quit"
        echo -ne "${RESET}"

        # Get keypress
        local keypress=$(get_key)

        case "$keypress" in
            "UP")
                [ $selected -gt 0 ] && selected=$((selected - 1))
                ;;
            "DOWN")
                [ $selected -lt $((total - 1)) ] && selected=$((selected + 1))
                ;;
            "ENTER")
                return $selected
                ;;
            "q"|"Q")
                return 255
                ;;
        esac
    done
}

# Main program
setup_terminal
trap restore_terminal EXIT

while true; do
    menu_options=(
        "Check or Install Dependencies"
        "Install LiveryWorks"
        "Install Addon"
        "Exit Program"
    )

    show_menu "${menu_options[@]}"
    choice=$?

    case $choice in
        0)
            show_message "Check or Install Dependencies" \
                "You may be prompted to enter password" \
                "for SUDO Press Enter to continue"
               sleep 3
               echo -e "\n${YELLOW_B}Running...${RESET}"
               sleep 1
               echo "Checking for Python3..."
               if command -v python3 &>/dev/null; then
                    echo -e "${GREEN}Python 3 is already installed: $(python3 --version)${RESET}"
                else
                    echo "Python 3 not found. Attempting to install..."

                    # Attempt to detect OS to use the correct package manager.
                    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
                        if command -v apt-get &>/dev/null; then
                            #Debian/Ubuntu
                            sudo apt-get update
                            sudo apt-get install -y python3
                        elif command -v dnf &>/dev/null; then
                            #Fedora/RHEL/CentOS
                            sudo dnf install -y python3
                        elif command -v yum &>/dev/null; then
                            #Older CentOS
                            sudo yum install -y python3
                        fi
                    elif [[ "$OSTYPE" == "darwin"* ]]; then
                        #MacOS checks for homebrew.
                        if command -v brew &>/dev/null; then
                            brew install python
                        else
                            echo -e "${RED_BOLD}ERROR:${RESET} Homebrew is not installed. Please install it."
                            exit 1
                        fi
                    else
                        echo -e "${RED_BOLD}ERROR:${RESET} Unsupported OS: $OSTYPE. Please install Python 3 manually."
                        exit 1
                    fi

                    #Verify installation
                    if command -v python3 &>/dev/null; then
                        echo -e "${GREEN}Successfully installed $(python3 --version)${RESET}"
                    else
                        echo -e "${YELLOW_B}Installation failed${RESET}"
                    fi
                fi

                echo "Checking for pip..."
                if command -v pip &>/dev/null; then
                    echo -e "${GREEN}pip is already installed: $(pip3 --version)${RESET}"
                else
                    echo "pip not found. Attempting to install..."

                    # Attempt to detect OS to use the correct package manager.
                    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
                        if command -v apt-get &>/dev/null; then
                            #Debian/Ubuntu
                            sudo apt-get update
                            sudo apt-get install -y python3-pip
                        elif command -v dnf &>/dev/null; then
                            #Fedora/RHEL/CentOS
                            sudo dnf install -y python3-pip
                        elif command -v yum &>/dev/null; then
                            #Older CentOS
                            sudo yum install -y python3-pip
                        fi
                    elif [[ "$OSTYPE" == "darwin"* ]]; then
                        #MacOS checks for homebrew.
                        if command -v brew &>/dev/null; then
                            python3 -m ensurepip --upgrade
                        else
                            echo -e "${RED_BOLD}ERROR:${RESET} Homebrew is not installed. Please install it."
                            exit 1
                        fi
                    else
                        echo -e "${RED_BOLD}ERROR:${RESET} Unsupported OS: $OSTYPE. Please install Python 3 manually."
                        exit 1
                    fi

                    #Verify installation
                    if command -v pip3 &>/dev/null; then
                        echo -e "${GREEN}Successfully installed $(pip3 --version)${RESET}"
                    else
                        echo -e "${YELLOW_B}Installation failed${RESET}"
                    fi
                fi

                # Function to check and install a single Python package
                check_and_install() {
                    local package=$1
                    local apt_pkg=$2
                    local dnf_pkg=$3

                    echo "Checking for $package..."

                    # 1. Check if already installed
                    if python3 -c "import $package" &> /dev/null; then
                        echo -e "${GREEN}$package is already installed.${RESET}"
                        echo "--------------------------------------"
                        return 0
                    fi

                    echo -e "${YELLOW_B}$package not found.${RESET} Detecting package manager..."

                    # 2. Identify OS and install via system package manager
                    if [ -f /etc/debian_version ]; then
                        echo "Debian/Ubuntu detected. Installing via apt..."
                        sudo apt-get update && sudo apt-get install -y "$apt_pkg"
                    elif [ -f /etc/redhat-release ] || [ -f /etc/fedora-release ]; then
                        echo "RHEL/Fedora detected. Installing via dnf..."
                        sudo dnf install -y "$dnf_pkg"
                    else
                        # Fallback to pip only if system package manager is unknown
                        echo "Unknown OS. Attempting pip installation..."
                        python3 -m pip install "$package" --break-system-packages
                    fi

                    # 3. Final verification
                    if python3 -c "import $package" &> /dev/null; then
                        echo -e "${GREEN}$package installed successfully.${RESET}"
                    else
                        echo -e "${RED_BOLD}ERROR:${RESET} Critical failure. Could not install $package."
                    fi
                    echo "--------------------------------------"
                }

                # Run the function for each package with their respective system manager names
                # Format: check_and_install "Python_Import_Name" "APT_Package_Name" "DNF_Package_Name"

                check_and_install "PyQt5"         "python3-pyqt5"    "python3-qt5"
                check_and_install "OpenGL"        "python3-opengl"   "python3-PyOpenGL"
                check_and_install "numpy"         "python3-numpy"    "python3-numpy"
                check_and_install "PIL"           "python3-pil"      "python3-pillow"
                check_and_install "trimesh"       "python3-trimesh"  "python3-trimesh"
                check_and_install "svgpathtools"  "python3-svgpathtools" "python3-svgpathtools"


                echo "Exiting to menu soon..."
                sleep 3
            ;;
        1)
            show_message "Install LiveryWorks" \
                "You may be prompted to enter password" \
                "for SUDO Press Enter to continue"
                echo -e "\n${YELLOW_B}NOTICES!${RESET}"
                sleep 2
                echo -e "${RED_BOLD}IF an older/another version is installed it is recommended to remove that version before installing.${RESET}"
                sleep 2
                echo -e "You will be given 5 second to cancel before installation begins, if you wish to cancel press ${YELLOW_B}CTRL + C${RESET}"

                # 5 Sec. progress bar.
                for i in $(seq 1 $BAR_LENGTH); do
                    PERCENT=$((i * 100 / BAR_LENGTH))
                    FILLED=$((i * BAR_LENGTH / BAR_LENGTH))
                    EMPTY=$((BAR_LENGTH - FILLED))

                    FILLED_BAR=$(printf "%0.s#" $(seq 1 $FILLED))
                    EMPTY_BAR=$(printf "%0.s-" $(seq 1 $EMPTY))

                    printf "\r[%s%s] %d%%" "$FILLED_BAR" "$EMPTY_BAR" "$PERCENT"
                    sleep 0.1
                done
                echo -e "\nStarting!"
                sleep 2
                echo "Creating directory: $TARGET_DIR"
                mkdir -p "$TARGET_DIR"
                echo "Downloading..."
                curl -L -# "$ZIP_URL" -o "$TEMP_ZIP"

                #Unzip the file and extraction process
                if [ -f "$TEMP_ZIP" ]; then
                    echo "Extracting files to $TARGET_DIR"
                    unzip -o "$TEMP_ZIP" -d "$TARGET_DIR" | awk 'BEGING {ORS="\r"} {print "Extracted " NR " files..."}'
                    echo -e "\nExtraction complete!"

                    rm "$TEMP_ZIP"
                else
                    echo -e "${RED_BOLD}ERROR:${RESET} Download failed."
                    exit 1
                fi

                echo -e "${GREEN}Successfull Installation: Installed $TARGET_DIR${RESET}"
            ;;
        2)
            show_message "Install Addon" \
                "You may be prompted to enter password" \
                "for SUDO Press Enter to continue"
                # Get the current logged-in user
            echo -e "\n"
            CURRENT_USER=$(logname 2>/dev/null || echo $SUDO_USER)
            if [ -z "$CURRENT_USER" ]; then
                CURRENT_USER=$(whoami)
            fi

            # Define the base path
            BASE_PATH="/home/${CURRENT_USER}/Documents/LWE/addons"
            LWE_PATH="/home/${CURRENT_USER}/Documents/LWE"

            # Check if LWE folder exists
            if [ ! -d "$LWE_PATH" ]; then
                echo -e "${RED_BOLD}ERROR:${RESET} LWE folder not found at $LWE_PATH"
                sleep 2
                continue
            fi

            # Check if addons folder exists
            if [ ! -d "$BASE_PATH" ]; then
                echo -e "${RED_BOLD}ERROR:${RESET} addons folder not found at $BASE_PATH"
                sleep 2
                continue
            fi

            echo -e "${GREEN}Found LWE and addons folders successfully.${RESET}"

            # Use safe_read_input to get the zip path (handles terminal mode switching)
            safe_read_input "Enter the path to the zip file: " ZIP_PATH

            # Check if zip file exists
            if [ ! -f "$ZIP_PATH" ]; then
                echo -e "${RED_BOLD}ERROR:${RESET} Zip file not found at $ZIP_PATH"
                sleep 2
                continue
            fi

            # Create a temporary directory for extraction
            TEMP_DIR=$(mktemp -d)
            echo "Created temporary directory: $TEMP_DIR"

            # Extract the zip file
            echo "Extracting zip file..."
            unzip -q "$ZIP_PATH" -d "$TEMP_DIR"

            # List contents for debugging
            echo "Contents of extracted zip:"
            ls -la "$TEMP_DIR"

            # Find the addon package directory (should be the only directory at top level, starting with ADDON_)
            ADDON_PACKAGE=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "ADDON_*" -print -quit)

            if [ -z "$ADDON_PACKAGE" ]; then
                # If no ADDON_ folder found, look for any directory containing data.json
                ADDON_PACKAGE=$(find "$TEMP_DIR" -type f -name "data.json" -print -quit | xargs dirname 2>/dev/null)
            fi

            if [ -z "$ADDON_PACKAGE" ]; then
                echo -e "${RED_BOLD}ERROR:${RESET} No addon package found inside the zip file"
                echo "Expected structure: ADDON_*/ folder with data.json and addon folder inside"
                rm -rf "$TEMP_DIR"
                sleep 2
                continue
            fi

            echo -e "${GREEN}Found addon package: $(basename "$ADDON_PACKAGE")${RESET}"

            # Find data.json in the addon package
            DATA_JSON=$(find "$ADDON_PACKAGE" -maxdepth 1 -name "data.json" -print -quit)

            if [ -z "$DATA_JSON" ]; then
                echo -e "${RED_BOLD}ERROR:${RESET} No data.json found in addon package"
                rm -rf "$TEMP_DIR"
                sleep 2
                continue
            fi

            echo "Found data.json"

            # Find the actual addon folder (any directory inside ADDON_PACKAGE that's not a hidden folder)
            ADDON_FOLDER=$(find "$ADDON_PACKAGE" -maxdepth 1 -type d ! -name ".*" ! -path "$ADDON_PACKAGE" -print -quit)

            if [ -z "$ADDON_FOLDER" ]; then
                echo -e "${RED_BOLD}ERROR:${RESET} No addon folder found inside the package"
                echo "Contents of package:"
                ls -la "$ADDON_PACKAGE"
                rm -rf "$TEMP_DIR"
                sleep 2
                continue
            fi

            ADDON_FOLDER_NAME=$(basename "$ADDON_FOLDER")
            echo -e "${GREEN}Found addon folder: $ADDON_FOLDER_NAME${RESET}"

            # Move the addon folder to the addons directory
            TARGET_ADDON="$BASE_PATH/$ADDON_FOLDER_NAME"
            if [ -d "$TARGET_ADDON" ]; then
                echo "Removing existing addon folder: $ADDON_FOLDER_NAME"
                rm -rf "$TARGET_ADDON"
            fi

            echo "Moving addon folder to $BASE_PATH..."
            mv "$ADDON_FOLDER" "$BASE_PATH/"

            # Process data.json
            TARGET_DATA_JSON="$BASE_PATH/data.json"
            if [ ! -f "$TARGET_DATA_JSON" ]; then
                echo "Creating new data.json file..."
                echo "[]" > "$TARGET_DATA_JSON"
            fi

            # Append the content of the extracted data.json to the target data.json
            echo "Appending data from extracted data.json to $TARGET_DATA_JSON..."

            # Use jq for proper JSON merging (if available)
            if command -v jq >/dev/null 2>&1; then
                # Create a backup
                cp "$TARGET_DATA_JSON" "${TARGET_DATA_JSON}.backup"

                # Check if source data.json is valid JSON
                if jq empty "$DATA_JSON" 2>/dev/null; then
                    # Merge JSON arrays (assuming both are arrays)
                    jq -s '.[0] + .[1]' "$TARGET_DATA_JSON" "$DATA_JSON" > "${TARGET_DATA_JSON}.tmp"
                    mv "${TARGET_DATA_JSON}.tmp" "$TARGET_DATA_JSON"
                    echo "JSON merged successfully"
                else
                    echo -e "${YELLOW_B}WARNING:${RESET} Source data.json is not valid JSON. Appending as text."
                    cat "$DATA_JSON" >> "$TARGET_DATA_JSON"
                fi
            else
                # Fallback: simple append (may not be valid JSON if arrays)
                echo -e "${YELLOW_B}WARNING:${RESET} jq not installed. Performing simple text append."
                cat "$DATA_JSON" >> "$TARGET_DATA_JSON"
            fi

            # Clean up temporary directory
            rm -rf "$TEMP_DIR"

            echo -e "${GREEN}Successfully processed the addon package.${RESET}"
            echo "Addon folder moved to: $BASE_PATH/$ADDON_FOLDER_NAME"
            echo "Data appended to: $TARGET_DATA_JSON"
            if [ -f "${TARGET_DATA_JSON}.backup" ]; then
                echo "Backup created at: ${TARGET_DATA_JSON}.backup"
            fi

            # Wait for user to see results
            echo ""
            echo "Press Enter to continue..."
            # Temporarily restore terminal for the final read
            saved_stty=$(stty -g)
            stty "$old_stty"
            printf '\033[?25h'
            read
            stty -echo -icanon min 1 time 0
            printf '\033[?25l'
            ;;
        3|255)
            show_message "GOODBYE!" \
                "Thank you, for using LiveryWorks and" \
                "services!" \
                "" \
                "EAV Colorful Menu: 2.3.2 Build 8."
            restore_terminal
            exit 0
            ;;
    esac
done
