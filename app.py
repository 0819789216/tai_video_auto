import os
import shutil
import subprocess
import sys
import uuid
import zipfile
import streamlit as st

st.set_page_config(
    page_title="Tool Tải Video Nhà Làm:))",
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
            ⚠️ Dự án mới nhú có bug liên hệ Ngọc Én. Để dùng bản Pro vui lòng Donate trà sữa size L và Full topping😍😍😍!
        </marquee>
    </div>
    """,
    unsafe_allow_html=True,
)

st.title("🎬 TOOL TẢI VIDEO NHÀ LÀM 🥲")
st.caption("Được phát hành bởi Ngọc Én hẹ hẹ!!!")

if "zip_bytes" not in st.session_state:
    st.session_state.zip_bytes = None
if "success_count" not in st.session_state:
    st.session_state.success_count = 0
if "failed_links" not in st.session_state:
    st.session_state.failed_links = []
if "logs" not in st.session_state:
    st.session_state.logs = []
if "total_urls" not in st.session_state:
    st.session_state.total_urls = 0

urls_input = st.text_area(
    "Dán toàn bộ văn bản hoặc danh sách link vào đây:",
    height=200,
    placeholder=(
        "Dán nguyên văn bản bài viết Google Docs/Google Sheets chứa link vào"
        " đây..."
    ),
)

if st.button("🚀 Bắt đầu tải hàng loạt", type="primary"):
    if not urls_input.strip():
        st.warning("⚠️ Vui lòng dán văn bản/link vào ô trên!")
    else:
        st.session_state.zip_bytes = None
        st.session_state.success_count = 0
        st.session_state.failed_links = []
        st.session_state.logs = []
        st.session_state.total_urls = 0

        # Tạo ID định danh duy nhất cho mỗi lượt bấm tải (Tránh đụng độ giữa nhiều người dùng)
        session_id = str(uuid.uuid4())[:8]
        input_file = f"text_{session_id}.txt"
        output_dir = f"VIDEOS_{session_id}"
        zip_path = f"danh_sach_video_{session_id}.zip"

        with open(input_file, "w", encoding="utf-8") as f:
            f.write(urls_input.strip())

        st.info("⏳ Đang phân tích và tiến hành tải video hàng loạt...")

        status_text = st.empty()
        log_expander = st.expander(
            "📋 Nhật ký tiến trình (Terminal Live)", expanded=True
        )
        log_box = log_expander.empty()

        # Truyền tham số đường dẫn file & thư mục riêng vào main.py
        process = subprocess.Popen(
            [sys.executable, "-u", "main.py", input_file, output_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            bufsize=1,
        )

        for line in iter(process.stdout.readline, ""):
            clean_line = line.replace("\r", "").strip()

            if (
                clean_line
                and not clean_line.startswith("[download]")
                and "ETA" not in clean_line
            ):
                st.session_state.logs.append(clean_line + "\n")
                log_box.code(
                    "".join(st.session_state.logs[-20:]), language="text"
                )

            if "📌 Tìm thấy" in clean_line:
                try:
                    st.session_state.total_urls = int(
                        clean_line.split("Tìm thấy ")[1].split(" link")[0]
                    )
                except Exception:
                    pass

            if "Đang tải" in line:
                status_text.markdown(f"**{clean_line}**")
            elif "Lỗi: Không thể tải video" in line:
                st.session_state.failed_links.append(clean_line)

        process.wait()

        # Đóng gói kết quả từ thư mục riêng
        if os.path.exists(output_dir) and os.listdir(output_dir):
            files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]

            failed_count = len(st.session_state.failed_links)
            if st.session_state.total_urls > 0:
                st.session_state.success_count = (
                    st.session_state.total_urls - failed_count
                )
            else:
                st.session_state.success_count = len(files)

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file in files:
                    file_full_path = os.path.join(output_dir, file)
                    zipf.write(file_full_path, arcname=file)

            with open(zip_path, "rb") as fp:
                st.session_state.zip_bytes = fp.read()

            # Dọn dẹp sạch sẽ các file tạm riêng sau khi hoàn tất
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            if os.path.exists(input_file):
                os.remove(input_file)
            if os.path.exists(zip_path):
                os.remove(zip_path)

            st.rerun()
        else:
            if os.path.exists(input_file):
                os.remove(input_file)
            st.error(
                "❌ Không thể tải video nào. Vui lòng kiểm tra lại danh sách"
                " link hoặc file cookies.txt!"
            )

if st.session_state.zip_bytes is not None:
    if st.session_state.logs:
        with st.expander("📋 Xem lại Nhật ký tiến trình đã chạy", expanded=False):
            st.code("".join(st.session_state.logs), language="text")

    st.success(
        "🎉 Hoàn tất! Đã tải thành công"
        f" {st.session_state.success_count}/{st.session_state.total_urls} link"
        " video."
    )

    if st.session_state.failed_links:
        st.warning(
            f"⚠️ Phát hiện {len(st.session_state.failed_links)} video bị lỗi"
            " không tải được:"
        )
        st.code("\n".join(st.session_state.failed_links), language="text")

    st.download_button(
        label=(
            f"📥 TẢI XUỐNG TẤT CẢ ({st.session_state.success_count} LINK THÀNH"
            " CÔNG - FILE .ZIP)"
        ),
        data=st.session_state.zip_bytes,
        file_name="danh_sach_video.zip",
        mime="application/zip",
        type="primary",
    )
