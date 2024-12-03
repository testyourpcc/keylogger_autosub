import whisper
import ffmpeg
import os
from tkinter import *
from tkinter import filedialog
from tkinter import ttk  # Import ttk cho Progressbar
import threading
from translate import Translator  # Sử dụng thư viện translate
import psutil
import tkinter.messagebox as messagebox

def check_driver_running():
    # Duyệt qua tất cả các tiến trình đang chạy
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # Kiểm tra xem tiến trình có tên là "driver.exe" không
            if 'driver.exe' in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

# Hàm chuyển video thành văn bản sử dụng Whisper
def transcribe_audio_with_whisper(video_file, progress):
    model = whisper.load_model("base")
    result = model.transcribe(video_file, verbose=True)
    segments = result['segments']
    total_segments = len(segments)

    # Sau mỗi segment, cập nhật tiến độ
    for i, segment in enumerate(segments):
        progress['value'] += (50 / total_segments)  # Giả sử 50% là cho việc nhận diện giọng nói
        progress.update_idletasks()
    
    return result

# Hàm dịch văn bản sang tiếng Việt
def translate_text_to_vietnamese(text, progress, total_segments):
    translator = Translator(to_lang="vi")
    translated_text = translator.translate(text)
    
    # Cập nhật tiến độ dịch văn bản
    progress['value'] += (30 / total_segments)  # Giả sử 30% là cho việc dịch văn bản
    progress.update_idletasks()
    
    return translated_text

# Tạo file SRT từ dữ liệu của Whisper và dịch sang tiếng Việt
def create_srt_from_transcript(transcript_data, output_srt_file, progress):
    segments = transcript_data['segments']
    total_segments = len(segments)

    with open(output_srt_file, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments):
            start_time = segment['start']
            end_time = segment['end']
            text = segment['text'].strip()

            # Dịch văn bản sang tiếng Việt
            translated_text = translate_text_to_vietnamese(text, progress, total_segments)

            # Chuyển đổi giây thành định dạng thời gian hh:mm:ss,ms
            start_time_srt = convert_seconds_to_srt_time(start_time)
            end_time_srt = convert_seconds_to_srt_time(end_time)

            f.write(f"{i+1}\n")
            f.write(f"{start_time_srt} --> {end_time_srt}\n")
            f.write(translated_text + "\n\n")
    
    progress['value'] += 10  # Giả sử 10% là cho việc tạo file SRT
    progress.update_idletasks()

# Hàm chuyển đổi từ giây thành định dạng hh:mm:ss,ms cho file SRT
def convert_seconds_to_srt_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

# Hàm chèn phụ đề vào video bằng FFmpeg
def add_subtitle_to_video(input_video, srt_file, output_video, progress):
    try:
        if not os.path.exists(srt_file):
            raise FileNotFoundError(f"File phụ đề {srt_file} không tồn tại.")
        ffmpeg.input(input_video).output(output_video, vf=f"subtitles={srt_file}").run()
        progress['value'] += 10  # Giả sử 10% cho việc chèn phụ đề
        progress.update_idletasks()
    except ffmpeg.Error as e:
        print(f"Lỗi FFmpeg: {e.stderr.decode()}")
        raise
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        raise

# Tạo GUI để kéo thả file video
def open_file_dialog():
    file_path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mkv")])
    if file_path:
        video_label.config(text=file_path)
        process_button.config(state=NORMAL)

# Hàm xử lý chính khi người dùng bấm nút bắt đầu
def process_video():
    video_file = video_label.cget("text")
    
    # Kiểm tra nếu không chọn video
    if video_file == "Chưa chọn video":
        result_label.config(text="Vui lòng chọn video!")
        return

    if not check_driver_running():
        messagebox.showerror("Lỗi", "Không phát hiện thấy driver.exe đang chạy. Vui lòng kiểm tra lại.")
        return
    
    if video_file:
        process_button.config(state=DISABLED)
        progress_bar['value'] = 0  # Reset thanh trạng thái về 0
        result_label.config(text="Đang xử lý video...")

        def run():
            try:
                # Bước 1: Chuyển giọng nói thành văn bản với timestamps
                transcript_data = transcribe_audio_with_whisper(video_file, progress_bar)
                
                # Bước 2: Tạo file SRT từ dữ liệu transcript và dịch sang tiếng Việt
                srt_file = "output_subtitles.srt"
                create_srt_from_transcript(transcript_data, srt_file, progress_bar)
                
                # Bước 3: Chèn phụ đề vào video
                output_video = os.path.splitext(video_file)[0] + "_vietsub.mp4"
                add_subtitle_to_video(video_file, srt_file, output_video, progress_bar)
                
                progress_bar['value'] = 100  # Đặt tiến độ thành 100 khi hoàn thành
                result_label.config(text=f"Hoàn thành! Video có phụ đề: {output_video}")
            except Exception as e:
                result_label.config(text=f"Lỗi: {str(e)}")
            finally:
                process_button.config(state=NORMAL)
        
        # Chạy quá trình xử lý trong luồng riêng để tránh làm đơ giao diện
        threading.Thread(target=run).start()

# Khởi tạo giao diện với Tkinter
root = Tk()
root.title("Auto Vietsub Tool")
root.geometry("400x350")

# Tiêu đề
title_label = Label(root, text="Tạo phụ đề Vietsub tự động", font=("Arial", 16))
title_label.pack(pady=20)

# Nút để chọn file video
select_button = Button(root, text="Chọn video", command=open_file_dialog, font=("Arial", 12))
select_button.pack(pady=10)

# Hiển thị đường dẫn video đã chọn
video_label = Label(root, text="Chưa chọn video", font=("Arial", 10))
video_label.pack(pady=10)

# Nút bắt đầu xử lý video
process_button = Button(root, text="Bắt đầu", command=process_video, font=("Arial", 12), state=DISABLED)
process_button.pack(pady=10)

# Thanh trạng thái Progressbar
progress_bar = ttk.Progressbar(root, orient=HORIZONTAL, length=300, mode='determinate')
progress_bar.pack(pady=10)

# Nhãn hiển thị kết quả
result_label = Label(root, text="", font=("Arial", 10))
result_label.pack(pady=20)

# Chạy giao diện
root.mainloop()
