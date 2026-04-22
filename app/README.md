# App

## Development
In windows, do these:
- notepad $env:USERPROFILE\.wslconfig
- In that file, paste this: 
[wsl2]
networkingMode=mirrored
- wsl --shutdown
- in powershell as admin: New-NetFirewallRule -DisplayName "Expo Metro Bundler" -Direction Inbound -LocalPort 8081 -Protocol TCP -Action Allow

In wsl, do these:
- npx expo start --host lan