#!/bin/bash

# Exit on errors
set -e

CHROME_DEB_URL="https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
CHROME_RPM_URL="https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm"
DEPENDENCIES=("wget" "curl" "dpkg" "apt-get" "snap")

# Function to check if a program is installed
check_installation() {
    if command -v "$1" &>/dev/null; then
        echo "$1 is already installed."
    else
        echo "$1 is not installed. Attempting to install..."
        return 1
    fi
}

install_dependencies() {
    for dep in "${DEPENDENCIES[@]}"; do
        if ! check_installation "$dep"; then
            sudo apt-get update
            sudo apt-get install -y "$dep"
        fi
    done
}

install_chrome() {
    if command -v google-chrome &>/dev/null; then
        echo "Google Chrome is already installed."
    else
        echo "Installing Google Chrome..."
        if [ -f /etc/debian_version ]; then
            wget -q $CHROME_DEB_URL -O google-chrome.deb
            sudo dpkg -i google-chrome.deb || sudo apt-get -f install -y
            rm google-chrome.deb
        elif [ -f /etc/redhat-release ]; then
            wget -q $CHROME_RPM_URL -O google-chrome.rpm
            sudo yum localinstall -y google-chrome.rpm
            rm google-chrome.rpm
        elif [ -f /etc/arch-release ]; then
            echo "Detected Arch-based distribution."
            sudo pacman -Syu --noconfirm
            wget -q $CHROME_RPM_URL -O google-chrome.rpm
            sudo pacman -U --noconfirm google-chrome.rpm
            rm google-chrome.rpm
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
    fi
}

install_python_dependencies() {
    echo "Installing Python dependencies..."
    if command -v pip &>/dev/null; then
        pip install -r requirements.txt
    else
        echo "Python pip is not installed. Installing pip..."
        sudo apt-get install -y python3-pip
        pip install -r requirements.txt
    fi
}

main() {
    echo "Starting installation process..."
    install_dependencies
    install_chrome
    install_python_dependencies
    echo "Installation complete!"
}

main
