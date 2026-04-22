FROM ubuntu:24.04

RUN apt-get update && apt-get install -y

RUN curl -s "https://get.sdkman.io" | bash
RUN source "$HOME/.sdkman/bin/sdkman-init.sh"

RUN sdk install java 25.0.2-tem