import os
import shutil
import subprocess
import sys
import zipfile
import streamlit as st

st.set_page_config(
    page_title="Công Cụ Tải Video Đa Nền Tảng (Bulk Download)",
    page_icon="🎬",
    layout="centered",
)

st.title("🎬 Công Cụ Tải Video Đa Nền Tảng")
st.caption(
    "Hỗ trợ copy/paste nguyên bài Docs/Text chứa hàng trăm link (Douyin, TikTok, Threads, Insta, Drive...)"
)

# Khung nhập văn bản/link
urls_input = st.text_area(
    "Dán toàn bộ văn bản hoặc danh sách link vào đây:",
    height=250,
    placeholder="Dán nguyên văn bản bài viết Google Docs chứa link vào đây...",
)

if st.button("🚀 Bắt đầu tải hàng loạt", type="primary"):
    if not urls_input.strip():
        st.warning("⚠️ Vui lòng dán văn bản/link vào ô trên!")
    else:
        # 1. Ghi nội dung vào file text.txt
        with open("text.txt", "w", encoding="utf-8") as f:
            f.write(urls_input.strip())

        output_dir = "downloaded_videos"
        zip_path = "danh_sach_video_hoan_thanh.zip"

        # Dọn dẹp thư mục cũ trước khi tải mới
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        if os.path.exists(zip_path):
            os.remove(zip_path)

        st.info("⏳ Đang phân tích và tiến hành tải video hàng loạt...")

        # Tạo khung hiển thị tiến trình và log thu gọn
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_expander = st.expander("📋 Xem chi tiết tiến trình tải", expanded=True)
        log_box = log_expander.empty()

        # 2. Chạy file main.py và bắt luồng dữ liệu log trực tiếp
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )

        logs = []
        for line in iter(process.stdout.readline, ""):
            logs.append(line)
            # Chỉ hiển thị 15 dòng log mới nhất để giao diện web không bị đơ
            log_box.code("".join(logs[-15:]), language="text")

            # Cập nhật thông báo ngắn
            if "Đang tải" in line:
                status_text.text(f"🔄 {line.strip()}")

        process.wait()

        # 3. Nén file và tạo nút Download
        if os.path.exists(output_dir) and os.listdir(output_dir):
            files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
            st.success(f"🎉 Đã hoàn tất tải thành công {len(files)} video!")

            status_text.text("📦 Đang đóng gói tất cả video thành file ZIP...")

            with zipfile.ZipFile(
                zip_path, "w", zipfile.ZIP_DEFLATED
            ) as zipf:
                for file in files:
                    file_full_path = os.path.join(output_dir, file)
                    zipf.write(file_full_path, arcname=file)

            # Nút tải xuống file ZIP duy nhất
            with open(zip_path, "rb") as fp:
                st.download_button(
                    label=f"📥 TẢI XUỐNG TẤT CẢ ({len(files)} VIDEO - FILE .ZIP)",
                    data=fp,
                    file_name="danh_sach_video.zip",
                    mime="application/zip",
                    type="primary",
                )

            # Dọn dẹp thư mục sau khi đóng gói xong để nhẹ server
            shutil.rmtree(output_dir)
        else:
            st.error(
                "❌ Không thể tải video. Vui lòng kiểm tra lại đường link hoặc file cookies.txt!"
            )