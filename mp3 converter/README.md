# YouTube to MP3 Converter

CLI-конвертер, который скачивает лучшее доступное аудио с YouTube и конвертирует его в MP3 через `ffmpeg`.

## Почему качество хорошее

- Сначала скачивается лучший доступный аудиопоток: `bestaudio/best`.
- MP3 создается через `libmp3lame`.
- По умолчанию используется `320 kbps`, что является практическим максимумом для MP3.
- В файл добавляются метаданные и обложка ролика, если YouTube отдает thumbnail.
- После конвертации показываются `BPM`, `Key` и `Alt Key` в Camelot-формате.
- Для BPM показываются также несколько кандидатов, потому что биты часто можно считать в half-time/double-time.
- `BPM` и `Key` записываются в ID3-теги, а рядом с MP3 создается файл `.analysis.txt`.

Важно: MP3 не может стать качественнее исходного аудио на YouTube. Этот конвертер сохраняет максимально разумное качество для MP3-формата.

Анализ тональности и BPM делается алгоритмически. Для сложных битов результат может немного отличаться от ручной разметки или DJ-софта.

По умолчанию анализ BPM предпочитает продюсерский диапазон `120-180`, поэтому для trap/drill/hip-hop чаще будет выбирать сетку проекта, а не half-time pulse. Для медленных битов можно поменять диапазон:

```bash
.venv/bin/python converter.py "URL" --bpm-min 70 --bpm-max 120
```

Используйте конвертер только для контента, на который у вас есть права или разрешение на скачивание.

## Установка

### 1. Установить ffmpeg

macOS:

```bash
brew install ffmpeg
```

Ubuntu/Debian:

```bash
sudo apt install ffmpeg
```

Windows:

```bash
winget install Gyan.FFmpeg
```

### 2. Установить Python-зависимости

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Использование

```bash
.venv/bin/python converter.py
```

После запуска вставьте ссылку и нажмите Enter.

Файлы по умолчанию сохраняются в папку `/Users/xerogi/Documents/Music/Beats`.

Для каждого бита создается отдельная папка с названием трека. MP3 и файл анализа называются только по названию трека, без YouTube id. Исходная ссылка сохраняется первой строкой внутри `.analysis.txt`.

Также можно передать ссылку сразу:

```bash
.venv/bin/python converter.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Выбрать папку:

```bash
python3 converter.py "https://www.youtube.com/watch?v=VIDEO_ID" -o ~/Music
```

Выбрать качество:

```bash
python3 converter.py "https://www.youtube.com/watch?v=VIDEO_ID" --quality best
python3 converter.py "https://www.youtube.com/watch?v=VIDEO_ID" --quality high
python3 converter.py "https://www.youtube.com/watch?v=VIDEO_ID" --quality medium
```

Скачать плейлист целиком:

```bash
python3 converter.py "https://www.youtube.com/playlist?list=PLAYLIST_ID" --playlist
```

Для age-restricted или приватных роликов можно передать cookies:

```bash
python3 converter.py "URL" --cookies ./cookies.txt
```

## Быстрая проверка

```bash
python3 converter.py --help
```
