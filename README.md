# Gesture Magic Battle

## フェーズ1：Webカメラによる手の追跡

一般的なWebカメラで最大2つの手を追跡します。各手のランドマーク21点と左右ラベル（`Left` または `Right`）に加え、1秒あたりの処理フレーム数と現在検出している手の数を画面に表示します。

### セットアップ

Python 3.11とWebカメラを用意し、リポジトリのルートディレクトリに移動します。以下は新しい `.venv` を作成する場合の例です。既存の仮想環境が別のPythonバージョンを使用している場合は、別のパスにPython 3.11の仮想環境を作成してください。

macOS

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
```

Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements.txt
```

[Hand Landmarkerモデル](https://huggingface.co/litert-community/MediaPipe-HandLandmarker-Full/resolve/74806d5014cdd5bd6ce94a80a0e4e93ae4cf2f9b/hand_landmarker.task)をダウンロードし、`.venv/hand_landmarker.task` に保存します。macOSでは `shasum -a 256 .venv/hand_landmarker.task`、Windowsでは `Get-FileHash .venv/hand_landmarker.task -Algorithm SHA256` を実行し、以下のハッシュ値と一致することを確認できます。[Googleサンプルに記載されたモデルのハッシュ値](https://github.com/google-ai-edge/mediapipe-samples/blob/main/.github/scripts/release_validate/spec/assets.json)

```text
fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1
```

### 実行と動作確認

macOS

```bash
.venv/bin/python -m app.hand_tracking --model .venv/hand_landmarker.task
```

Windows PowerShell

```powershell
.\.venv\Scripts\python.exe -m app.hand_tracking --model .venv/hand_landmarker.task
```

1. 両手を開いてカメラに映し、各手の点と接続線が動きに追従することを確認します。画面上の位置にかかわらず、自分の左手と右手に正しいラベルが付いていることを確認します。
2. 片手ずつ画面の外に出してから戻し、その手の表示が消えて再び表示されることを確認します。両手を画面の外に出すと `Hands: 0` と表示されます。
3. 照明が一定の場所で両手を動かし、`Q` または `Esc` で終了します。ターミナルに全体の処理FPSと、検出した手の数ごとのフレーム数が表示されます。このFPSには映像の取得と追跡処理の時間が含まれます。

既定のカメラを開けない場合は、OSのカメラ使用権限を確認してください。外付けカメラを使う場合は `--camera 1` を指定してみてください。録画済みの映像を使う場合は、同じ実行コマンドに `--video /path/to/video.mp4` を追加します。ウィンドウを表示せず処理統計だけを確認するには、`--headless` も追加します。

自動テストはリポジトリのルートディレクトリで、仮想環境のPythonに `-m unittest discover -s tests -v` を指定して実行します。テストの実行にWebカメラやモデルファイルは不要です。
