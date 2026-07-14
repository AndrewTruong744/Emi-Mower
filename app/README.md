# App

# Development

## In windows (if using WSL), do these:

- notepad $env:USERPROFILE\.wslconfig
- In that file, paste this:
  [wsl2]
  networkingMode=mirrored
- wsl --shutdown
- in powershell as admin: New-NetFirewallRule -DisplayName "Expo Metro Bundler" -Direction Inbound -LocalPort 8081 -Protocol TCP -Action Allow
- winget install --interactive --exact dorssel.usbipd-win

## In wsl, do these:

- sudo apt install android-tools-adb android-tools-fastboot
- echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0666", GROUP="plugdev"' | sudo tee /etc/udev/rules.d/51-android.rules
- sudo udevadm control --reload-rules
- sudo udevadm trigger

## nvm and npm

- curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.5/install.sh | bash
- source ~/.bashrc
- nvm install --lts
- nvm use --lts

### Java

- install sdk
- sdk install java 17.0.11-tem
- sdk default java 17.0.11-tem

### Android Development Tools

- mkdir -p $HOME/Android/Sdk/cmdline-tools
- wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
- unzip commandlinetools-linux-11076708_latest.zip -d $HOME/Android/Sdk/cmdline-tools
- mv $HOME/Android/Sdk/cmdline-tools/cmdline-tools $HOME/Android/Sdk/cmdline-tools/latest
- export PATH=$PATH:$HOME/Android/Sdk/cmdline-tools/latest/bin
- yes | sdkmanager --licenses
- sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"
- Add these to your .bashrc:
  export ANDROID_HOME=$HOME/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin
- source ~/.bashrc
- npm install
- npx expo run:android
- (if npx expo run:android fails, run this) echo "sdk.dir=/home/nateclickbait/Android/Sdk" > /home/nateclickbait/downloads/repos/Emi-Mower/app/android/local.properties

In your phone do these:

- enable developer settings
- enable usb debugging
- change from charge only to transfer files / android auto

### After every native package that talks or modifies kotlin/java, run these

- rm -rf android ios
- npx expo prebuild --platform android --clean
- npx expo run:android

### Linting and formatting

- npm run lint
- npx prettier --write .

# To run

## To connect phone to windows device

### In Windows:

- usbipd list
- usbipd bind --busid "number-number"
- usbipd attach --wsl --busid "number-number"

- npx expo start --host lan

# Important

- Currently configured only for android
