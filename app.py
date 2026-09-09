import os
import shutil
import subprocess
import sys
import zipfile
import streamlit as st

st.set_page_config(
    page_title="Công Cụ Tải Video Đa Nền Tảng",
    page_icon="🎬",
    layout="centered",
)

st.title("🎬 Công Cụ Tải Video Đa Nền Tảng")
st.caption(
    "Hỗ trợ copy/paste nguyên bài Docs/Text chứa hàng trăm link (Douyin, TikTok, Threads, Insta, Drive...)"
)

urls_input = st.text_area(
    "Dán toàn bộ văn bản hoặc danh sách link vào đây:",
    height=200,
    placeholder="Dán nguyên văn bản bài viết Google Docs chứa link vào đây...",
)

if st.button("🚀 Bắt đầu tải hàng loạt", type="primary"):
    if not urls_input.strip():
        st.warning("⚠️ Vui lòng dán văn bản/link vào ô trên!")
    else:
        with open("text.txt", "w", encoding="utf-8") as f:
            f.write(urls_input.strip())

        output_dir = "VIDEOS"
        zip_path = "danh_sach_video_hoan_thanh.zip"

        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        if os.path.exists(zip_path):
            os.remove(zip_path)

        st.info("⏳ Đang phân tích và tiến hành tải video hàng loạt...")

        status_text = st.empty()
        log_expander = st.expander("📋 Nhật ký tiến trình (Terminal Live)", expanded=True)
        log_box = log_expander.empty()

        process = subprocess.Popen(
            [sys.executable, "-u", "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            bufsize=1,
        )

        logs = []
        failed_links = []

        for line in iter(process.stdout.readline, ""):
            logs.append(line)
            # Giữ khung log cuộn xem được tối đa 20 dòng mới nhất
            log_box.code("".join(logs[-20:]), language="text")

            if "Đang tải" in line:
                status_text.markdown(f"**{line.strip()}**")
            elif "Lỗi: Không thể tải video" in line or "ERROR:" in line:
                failed_links.append(line.strip())

        process.wait()

        # Hiển thị kết quả
        if os.path.exists(output_dir) and os.listdir(output_dir):
            files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
            st.success(f"🎉 Hoàn tất! Đã tải thành công {len(files)} video.")

            # Báo tổng hợp danh sách link lỗi nếu có
            if failed_links:
                st.warning(f"⚠️ Phát hiện {len(failed_links)} video bị lỗi không tải được:")
                st.code("\n".join(failed_links), language="text")

            # Đóng gói ZIP
            status_text.text("📦 Đang đóng gói tất cả video thành file ZIP...")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file in files:
                    file_full_path = os.path.join(output_dir, file)
                    zipf.write(file_full_path, arcname=file)

            with open(zip_path, "rb") as fp:
                st.download_button(
                    label=f"📥 TẢI XUỐNG TẤT CẢ ({len(files)} VIDEO - FILE .ZIP)",
                    data=fp,
                    file_name="danh_sach_video.zip",
                    mime="application/zip",
                    type="primary",
                )

            shutil.rmtree(output_dir)
        else:
            st.error("❌ Không thể tải video nào. Vui lòng kiểm tra lại danh sách link hoặc file cookies.txt!")
