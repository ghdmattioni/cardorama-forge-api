#!/bin/sh
set -eu
: "${FORGE_VERSION:=2.0.16}"
url="https://github.com/Card-Forge/forge/releases/download/forge-${FORGE_VERSION}/forge-installer-${FORGE_VERSION}.tar.bz2"
mkdir -p /opt/forge
curl -fL --retry 4 --retry-delay 3 "$url" -o /tmp/forge.tar.bz2
tar -xjf /tmp/forge.tar.bz2 -C /opt/forge
rm /tmp/forge.tar.bz2
found=""
for pattern in 'run-forge.jar' 'forge-*-jar-with-dependencies.jar' 'forge.jar'; do
  found=$(find /opt/forge -type f -name "$pattern" | head -n 1)
  if [ -n "$found" ]; then break; fi
done
if [ -z "$found" ]; then
  echo "Installer has no identified runnable Forge jar; inspect official release layout" >&2
  find /opt/forge -type f -name '*.jar' | head -n 30 >&2
  exit 2
fi
if [ "$found" != "/opt/forge/forge.jar" ]; then ln -s "$found" /opt/forge/forge.jar; fi
printf '%s\n' "$FORGE_VERSION" > /opt/forge/version.txt
