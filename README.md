# 動画・音声文字起こし

動画・音声ファイルをデスクトップ画面から選び、ローカル環境の Whisper で文字起こしするアプリです。ファイルは外部サービスへ送信しません。

## 必要なもの

- Git
- Python 3.11〜3.13
- 初回セットアップおよびモデル取得時のインターネット接続

FFmpeg、Pythonパッケージ、Whisperモデルは初回利用時に自動で取得されます。FFmpegは `imageio-ffmpeg` のOS別Python wheelとして仮想環境内へ導入されるため、システム全体へのインストールや管理者権限は不要です。

## Windows 11

```powershell
git clone <リポジトリURL>
cd speech-to-text
.\run_windows.bat
```

`run_windows.bat` はダブルクリックでも起動できます。

## macOS

```bash
git clone <リポジトリURL>
cd speech-to-text
./run_macos.command
```

実行権限に関するエラーが出た場合は、次のコマンドを一度実行してください。

```bash
chmod +x run_macos.command scripts/setup_macos.sh
./run_macos.command
```

macOSがダウンロードしたスクリプトをブロックした場合は、Finderで `run_macos.command` をControlキーを押しながらクリックし、「開く」を選択してください。

## 使い方

1. 起動後にデスクトップアプリのウィンドウが開きます。
2. モデルと言語を選択します。最初は `small` と「自動判定」がおすすめです。
3. 動画または音声ファイルを選択し、「文字起こしを開始」を押します。
4. 結果をTXT、SRT、VTT形式で保存できます。

ファイルのドラッグ＆ドロップにも対応しています。

## GPUについて

NVIDIA GPUとドライバーが検出された場合はCUDAを優先します。GPU処理に失敗した場合は自動的にCPUで再試行します。GPUがないWindows PCとmacOSではCPUを使用します。現在の構成ではApple SiliconのMetal/MPSは使用しません。

モデルも初回の文字起こし時だけダウンロードされます。モデルが大きいほど一般に精度が上がりますが、ダウンロード容量、メモリ使用量、処理時間も増えます。

## 対応形式

MP3、WAV、M4A、AAC、FLAC、OGG、MP4、MOV、MKV、WebM、MPEGなど。ファイル内部のコーデックによっては変換できない場合があります。

## 開発とテスト

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

GitHub ActionsでもWindows/macOSとPython 3.11〜3.13の組み合わせをテストします。

## データとライセンスについて

- アップロードしたファイルと文字起こし処理はローカルで完結します。
- 初回にPythonパッケージとWhisperモデルを配布元からダウンロードします。
- 本アプリが利用する各ライブラリおよびFFmpegには、それぞれのライセンスが適用されます。
- 本アプリのソースコードはMIT Licenseで公開しています。詳しくは `LICENSE` を参照してください。
