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

# 1. Khởi tạo Session State giữ nguyên kết quả không bị mất khi nhấn nút Tải xuống
if "zip_bytes" not in st.session_state:
    st.session_state.zip_bytes = None
if "success_count" not in st.session_state:
    st.session_state.success_count = 0
if "failed_links" not in st.session_state:
    st.session_state.failed_links = []
if "logs" not in st.session_state:
    st.session_state.logs = []

urls_input = st.text_area(
    "Dán toàn bộ văn bản hoặc danh sách link vào đây:",
    height=200,
    placeholder="Dán nguyên văn bản bài viết Google Docs chứa link vào đây...",
)

if st.button("🚀 Bắt đầu tải hàng loạt", type="primary"):
    if not urls_input.strip():
        st.warning("⚠️ Vui lòng dán văn bản/link vào ô trên!")
    else:
        # Reset trạng thái mỗi khi nhấn tải lượt mới
        st.session_state.zip_bytes = None
        st.session_state.success_count = 0
        st.session_state.failed_links = []
        st.session_state.logs = []

        with open("text.txt", "w", encoding="utf-8") as f:
            f.write(urls_input.strip())

        # Tên thư mục khớp hoàn toàn với main.py (VIDEOS)
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

        # Khởi chạy main.py ở chế độ unbuffered (-u)
        process = subprocess.Popen(
            [sys.executable, "-u", "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            bufsize=1,
        )

        for line in iter(process.stdout.readline, ""):
            st.session_state.logs.append(line)
            # Giữ khung log cuộn xem 20 dòng mới nhất
            log_box.code("".join(st.session_state.logs[-20:]), language="text")

            if "Đang tải" in line:
                status_text.markdown(f"**{line.strip()}**")
            elif "Lỗi: Không thể tải video" in line:
                # Bắt đúng dòng báo lỗi chính thức từ main.py
                st.session_state.failed_links.append(line.strip())

        process.wait()

        # Kiểm tra kết quả trong thư mục VIDEOS
        if os.path.exists(output_dir) and os.listdir(output_dir):
            files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
            st.session_state.success_count = len(files)

            # Đóng gói ZIP
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file in files:
                    file_full_path = os.path.join(output_dir, file)
                    zipf.write(file_full_path, arcname=file)

            with open(zip_path, "rb") as fp:
                st.session_state.zip_bytes = fp.read()

            # Dọn dẹp thư mục tạm trên mây
            shutil.rmtree(output_dir)
            if os.path.exists(zip_path):
                os.remove(zip_path)

            st.rerun()
        else:
            st.error("❌ Không thể tải video nào. Vui lòng kiểm tra lại danh sách link hoặc file cookies.txt!")

# 2. KHU VỰC HIỂN THỊ KẾT QUẢ CỐ ĐỊNH (Không bị reset khi bấm Tải file)
if st.session_state.zip_bytes is not None:
    if st.session_state.logs:
        with st.expander("📋 Xem lại Nhật ký tiến trình đã chạy", expanded=False):
            st.code("".join(st.session_state.logs), language="text")

    st.success(f"🎉 Hoàn tất! Đã tải thành công {st.session_state.success_count} video.")

    if st.session_state.failed_links:
        st.warning(f"⚠️ Phát hiện {len(st.session_state.failed_links)} video bị lỗi không tải được:")
        st.code("\n".join(st.session_state.failed_links), language="text")

    st.download_button(
        label=f"📥 TẢI XUỐNG TẤT CẢ ({st.session_state.success_count} VIDEO - FILE .ZIP)",
        data=st.session_state.zip_bytes,
        file_name="danh_sach_video.zip",
        mime="application/zip",
        type="primary",
    )
