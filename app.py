import streamlit as st
import cv2
import numpy as np
import pandas as pd
import os

# 页面基础配置，开启 wide 模式
st.set_page_config(
    page_title="BioColor AI",
    page_icon="🔬",
    layout="wide"
)

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 4px; font-weight: bold; }
    .stFileUploader { width: 100%; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #1f2937;'>🔬 Microplate Array Colorimetric System</h1>", unsafe_allow_html=True)
st.write("")

# 动态加载根目录下的 curve.xlsx 中的 sheet 名作为下拉菜单选项
excel_path = "curve.xlsx"
sheet_names = ["miR-223", "miR-935", "miR-2284W", "test"]
if os.path.exists(excel_path):
    try:
        xls = pd.ExcelFile(excel_path)
        sheet_names = xls.sheet_names
    except Exception as e:
        pass

# 分栏比例 [10, 2]
col_left, col_right = st.columns([9, 3])

# 初始化 Session State
if "origin_img" not in st.session_state:
    st.session_state.origin_img = None
if "result_img" not in st.session_state:
    st.session_state.result_img = None

with col_right:
    st.markdown("### 🖼️ Operations")
    
    uploaded_file = st.file_uploader("Load Image", type=["png", "jpg", "jpeg", "bmp"], label_visibility="collapsed")
    
    reset_clicked = st.button("Reset", use_container_width=True)
    save_clicked = st.button("Save", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### ⚙️ Parameters")
    rows = st.slider("Rows", min_value=1, max_value=10, value=3)
    cols = st.slider("Cols", min_value=1, max_value=12, value=4)
    r_val = st.slider("Radius", min_value=1, max_value=8, value=5)
    r = r_val * 5 / 100
    precision = st.slider("Precision", min_value=3, max_value=5, value=4)
    
    st.markdown("---")
    st.markdown("### 📈 Curve")
    rna_type = st.selectbox("miR Type", sheet_names, label_visibility="collapsed")
    
    st.markdown("---")
    default_clicked = st.button("Default", use_container_width=True)
    count_clicked = st.button("Calculate", type="primary", use_container_width=True)

# 处理上传或拍照获取的图片
if uploaded_file is not None:
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img_decoded = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img_decoded is not None:
        st.session_state.origin_img = img_decoded
        st.session_state.result_img = img_decoded

# 重置按钮逻辑
if reset_clicked:
    if st.session_state.origin_img is not None:
        st.session_state.result_img = st.session_state.origin_img

with col_left:
    st.markdown("### Image Display Area")
    image_placeholder = st.empty()

    if st.session_state.result_img is not None:
        image_placeholder.image(cv2.cvtColor(st.session_state.result_img, cv2.COLOR_BGR2RGB), use_container_width=True)
    else:
        default_img_path = "img1.jpeg"
        if os.path.exists(default_img_path):
            default_img = cv2.imread(default_img_path)
            image_placeholder.image(cv2.cvtColor(default_img, cv2.COLOR_BGR2RGB), use_container_width=True)
        else:
            blank_img = np.zeros((600, 800, 3), dtype=np.uint8) + 240
            cv2.putText(blank_img, "Please load an image", (200, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (120, 120, 120), 2)
            image_placeholder.image(blank_img, use_container_width=True)

# 点击计算按钮时执行核心算法与曲线拟合
if count_clicked and st.session_state.origin_img is not None:
    with st.spinner(f'Executing analysis with curve fitting ({rna_type})...'):
        poly_coeffs = None
        if os.path.exists(excel_path):
            try:
                df_curve = pd.read_excel(excel_path, sheet_name=rna_type)
                x_vals = df_curve['相对灰度'].values
                y_vals = df_curve['lg(浓度)'].values
                deg = min(2, len(x_vals) - 1)
                poly_coeffs = np.polyfit(x_vals, y_vals, deg)
            except Exception as e:
                pass

        image = st.session_state.origin_img.copy()
        height, width = image.shape[:2]
        
        row_height = height // rows
        col_width = width // cols
        
        for i in range(1, rows):
            cv2.line(image, (0, i * row_height), (width, i * row_height), (255, 0, 0), 2)
        for j in range(1, cols):
            cv2.line(image, (j * col_width, 0), (j * col_width, height), (255, 0, 0), 2)
        
        data_matrix_avg = []
        temp_avgs = []
        
        for i in range(rows):
            for j in range(cols):
                cx = j * col_width + col_width // 2
                cy = i * row_height + row_height // 2
                rad = int(min(row_height, col_width) * r)
                sub = image[max(cy - rad, 0):min(cy + rad, height), max(cx - rad, 0):min(cx + rad, width)]
                if sub.size > 0:
                    avg_val = cv2.mean(cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY))[0]
                    temp_avgs.append(avg_val)
                else:
                    temp_avgs.append(0)
        
        base_gray = max(temp_avgs) if temp_avgs else 188

        idx = 0
        for i in range(rows):
            for j in range(cols):
                center_x = j * col_width + col_width // 2
                center_y = i * row_height + row_height // 2
                radius = int(min(row_height, col_width) * r)
                
                top_left_x = center_x - radius
                top_left_y = center_y - radius
                bottom_right_x = center_x + radius
                bottom_right_y = center_y + radius
                
                cv2.rectangle(image, (top_left_x, top_left_y), (bottom_right_x, bottom_right_y), (0, 0, 255), 2)
                
                avg_gray = float(f'{temp_avgs[idx]:.{precision}g}')
                diff_val = max(0, int(round(base_gray - avg_gray)))
                
                if poly_coeffs is not None:
                    lg_conc = np.polyval(poly_coeffs, diff_val)
                    exponent = int(round(lg_conc))
                    if exponent > 0:
                        density_val = f"1*10^{exponent}"
                    elif diff_val > 0:
                        density_val = f"1*10^{max(1, diff_val // 6)}"
                    else:
                        density_val = "0"
                else:
                    density_val = f"1*10^{max(1, diff_val // 6)}" if diff_val > 0 else "0"
                
                data_matrix_avg.append(avg_gray)
                
                font = cv2.FONT_HERSHEY_SIMPLEX
                scale = 1.1
                color = (0, 0, 255)
                thick = 2
                
                text_avg = f'Avg: {avg_gray}'
                text_diff = f'Diff: {diff_val}'
                text_den = f'Density: {density_val}'
                
                box_width = bottom_right_x - top_left_x
                box_height = bottom_right_y - top_left_y
                
                (t_w1, t_h1), _ = cv2.getTextSize(text_avg, font, scale, thick)
                (t_w2, t_h2), _ = cv2.getTextSize(text_diff, font, scale, thick)
                (t_w3, t_h3), _ = cv2.getTextSize(text_den, font, scale, thick)
                
                x_center_1 = top_left_x + max(2, (box_width - t_w1) // 2)
                x_center_2 = top_left_x + max(2, (box_width - t_w2) // 2)
                x_center_3 = top_left_x + max(2, (box_width - t_w3) // 2)
                
                total_text_height = t_h1 + t_h2 + t_h3 + 24
                y_start = top_left_y + (box_height - total_text_height) // 2 + t_h1
                
                cv2.putText(image, text_avg, (x_center_1, y_start), font, scale, color, thick, cv2.LINE_AA)
                cv2.putText(image, text_diff, (x_center_2, y_start + t_h2 + 10), font, scale, color, thick, cv2.LINE_AA)
                cv2.putText(image, text_den, (x_center_3, y_start + t_h2 + t_h3 + 20), font, scale, color, thick, cv2.LINE_AA)
                
                idx += 1

        st.session_state.result_img = image
        
        with col_left:
            image_placeholder.image(cv2.cvtColor(image, cv2.COLOR_BGR2RGB), use_container_width=True)
            st.success(f"Calculation complete using curve sheet: {rna_type}!")
            
            st.markdown("### 📊 Quantitative Matrix Data (Avg Summary)")
            data_df = pd.DataFrame(np.array(data_matrix_avg).reshape((rows, cols)))
            st.dataframe(data_df, use_container_width=True)

elif count_clicked and st.session_state.origin_img is None:
    st.warning("Please upload or load a microplate image first!")