import os
import shutil
import subprocess
import sys
import zipfile
import streamlit as st

st.set_page_config(
    page_title="Toll Tải Video Nhà Làm:))",
    page_icon="🎬",
    layout="centered",
)

st.markdown(
    """
    <style>
    .running-banner {
        position: fixed;
        top: 12px;
        left: 12px;
        z-index: 999999;
        background-color: #fff3cd;
        color: #856404;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 13px;
        border: 1px solid #ffeeba;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.08);
        width: 480px;
        max-width: 80vw;
        overflow: hidden;
        white-space: nowrap;
    }
    .running-banner marquee {
        vertical-align: middle;
    }
    </style>
    <div class="running-banner">
        <marquee behavior="scroll" direction="left" scrollamount="5">
            ⚠️ Dự án mới nhú có lỗi liên hệ Ngọc Én (HCNS). Để dùng bản Pro vui lòng donate trà sữa size L và full topping😍!
        </marquee>
    </div>
    """,
    unsafe_allow_html=True,
)

st.title("🎬 TOLL TẢI VIDEO NHÀ LÀM 🥲")
st.caption("Được phát hành bởi Ngọc Én hẹ hẹ!!!")

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
    placeholder="Dán nguyên văn bản bài viết Google Docs/Google Sheets chứa link vào đây...",
)

if st.button("🚀 Bắt đầu tải hàng loạt", type="primary"):
    if not urls_input.strip():
        st.warning("⚠️ Vui lòng dán văn bản/link vào ô trên!")
    else:
        st.session_state.zip_bytes = None
        st.session_state.success_count = 0
        st.session_state.failed_links = []
        st.session_state.logs = []

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

        for line in iter(process.stdout.readline, ""):
            # Lọc mọi biến thể của yt-dlp (có khoảng trắng, \r, hoặc viết hoa/thường)
            check_line = line.lower()
            if "[download]" not in check_line and "eta" not in check_line:
                clean_print = line.replace('\r', '').strip()
                if clean_print:
                    st.session_state.logs.append(clean_print + "\n")
                    log_box.code("".join(st.session_state.logs[-20:]), language="text")

            if "Đang tải" in line:
                status_text.markdown(f"**{line.strip()}**")
            elif "Lỗi: Không thể tải video" in line:
                st.session_state.failed_links.append(line.strip())

        process.wait()

        if os.path.exists(output_dir) and os.listdir(output_dir):
            files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
            st.session_state.success_count = len(files)

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file in files:
                    file_full_path = os.path.join(output_dir, file)
                    zipf.write(file_full_path, arcname=file)

            with open(zip_path, "rb") as fp:
                st.session_state.zip_bytes = fp.read()

            shutil.rmtree(output_dir)
            if os.path.exists(zip_path):
                os.remove(zip_path)

            st.rerun()
        else:
            st.error("❌ Không thể tải video nào. Vui lòng kiểm tra lại danh sách link hoặc file cookies.txt!")

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
