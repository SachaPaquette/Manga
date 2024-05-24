#!/bin/bash

# Function to check if a program is installed
check_installation() {
    if which $1 > /dev/null 2>&1; then
        echo "$1 is installed."
    else
        echo "$1 is not installed."
    fi
}

# Function to install a program using apt-get
install_program() {
    echo "Installing $1..."
    sudo apt-get install $1
    if [ $? -ne 0 ]; then
        echo "Error installing $1"
        exit 1
    fi
}

# Check the operating system
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Check if google-chrome is installed
    check_installation "google-chrome"
    
    # Install Google Chrome if not installed
    if ! which google-chrome > /dev/null 2>&1; then
        wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
        sudo dpkg -i google-chrome-stable_current_amd64.deb
        sudo apt-get install -f  
        rm google-chrome-stable_current_amd64.deb
    fi
else 
    echo "Operating system not supported."
    exit 1
fi

echo "Now installing Python's dependecies..."
