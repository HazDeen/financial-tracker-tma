#!/usr/bin/env bash
set -euo pipefail
FINANCE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$FINANCE_ROOT"
export JAVA_HOME="${FINANCE_JAVA_HOME:-$(/usr/libexec/java_home -v 21)}"
export PATH="$JAVA_HOME/bin:$PATH"
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
FINANCE_TOOLS="$ANDROID_HOME/build-tools/35.0.0"
FINANCE_JAR="$ANDROID_HOME/platforms/android-35/android.jar"
FINANCE_BUILD="$FINANCE_ROOT/android/app/build/sdk-release"
FINANCE_SIGN_DIR="${FINANCE_SIGN_DIR:-$HOME/.local/share/hazdeen-finance-signing}"
mkdir -p "$FINANCE_SIGN_DIR" "$FINANCE_BUILD/gen" "$FINANCE_BUILD/classes" "$FINANCE_BUILD/dex" output/android
chmod 700 "$FINANCE_SIGN_DIR"
if [ ! -f "$FINANCE_SIGN_DIR/release.jks" ]; then
  if [ ! -f "$FINANCE_SIGN_DIR/password" ]; then
    (umask 077; openssl rand -hex 32 > "$FINANCE_SIGN_DIR/password")
  fi
  "$JAVA_HOME/bin/keytool" -genkeypair -keystore "$FINANCE_SIGN_DIR/release.jks" -storetype PKCS12 -storepass:file "$FINANCE_SIGN_DIR/password" -keypass:file "$FINANCE_SIGN_DIR/password" -alias finance -keyalg RSA -keysize 3072 -validity 10000 -dname 'CN=Hazdeen Finance'
fi
# The SDK build uses only Android framework APIs, with no third-party native dependencies.
ANDROID_BUILD=1 VITE_API_URL=/api/v1 npm --prefix frontend run build
python3 - <<'PY'
from pathlib import Path
import shutil
assets=Path('android/app/src/main/assets/web')
if assets.exists(): shutil.rmtree(assets)
shutil.copytree('frontend/dist',assets)
manifest=Path('android/app/src/main/AndroidManifest.xml').read_text().replace('<manifest ', '<manifest package="xyz.hazdeen.finance" ', 1)
Path('android/app/build/sdk-release/AndroidManifest.xml').write_text(manifest)
PY
"$FINANCE_TOOLS/aapt" package -f -m -J "$FINANCE_BUILD/gen" -M "$FINANCE_BUILD/AndroidManifest.xml" -S android/app/src/main/res -A android/app/src/main/assets -I "$FINANCE_JAR" --min-sdk-version 26 --target-sdk-version 34 --version-code 4 --version-name 1.3.0 -F "$FINANCE_BUILD/unsigned.apk"
"$JAVA_HOME/bin/javac" -encoding UTF-8 -source 8 -target 8 -Xlint:deprecation -classpath "$FINANCE_JAR" -d "$FINANCE_BUILD/classes" android/app/src/main/java/xyz/hazdeen/finance/MainActivity.java
find "$FINANCE_BUILD/classes" -name '*.class' > "$FINANCE_BUILD/classes.txt"
"$FINANCE_TOOLS/d8" --lib "$FINANCE_JAR" --min-api 26 --output "$FINANCE_BUILD/dex" @"$FINANCE_BUILD/classes.txt"
(cd "$FINANCE_BUILD/dex" && zip -q -j "$FINANCE_BUILD/unsigned.apk" classes*.dex)
"$FINANCE_TOOLS/zipalign" -f -p 4 "$FINANCE_BUILD/unsigned.apk" "$FINANCE_BUILD/aligned.apk"
"$FINANCE_TOOLS/apksigner" sign --ks "$FINANCE_SIGN_DIR/release.jks" --ks-pass "file:$FINANCE_SIGN_DIR/password" --ks-key-alias finance --out output/android/moi-finansy-1.3.0.apk "$FINANCE_BUILD/aligned.apk"
"$FINANCE_TOOLS/apksigner" verify --verbose output/android/moi-finansy-1.3.0.apk
shasum -a 256 output/android/moi-finansy-1.3.0.apk > output/android/SHA256SUMS-1.3.0.txt
