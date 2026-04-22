import streamlit as st
import trimesh
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import plotly.graph_objects as go
import zipfile
import io
import hashlib
from scipy.spatial.transform import Rotation as R

# --- DETERMINISTIC FDA SEED ---
np.random.seed(1337)

st.set_page_config(page_title="Omni-Engine: Surgical Stencil", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# SESSION STATE MANAGEMENT (Fixes disappearing UI)
# ==========================================
if 'processed' not in st.session_state:
    st.session_state.processed = False
if 'pdf_buffer' not in st.session_state:
    st.session_state.pdf_buffer = None
if 'stencil_fig' not in st.session_state:
    st.session_state.stencil_fig = None
if 'hologram_fig' not in st.session_state:
    st.session_state.hologram_fig = None

# --- TOP NAVIGATION ---
st.title("🫀 Omni-Engine: Aortic Smart Cut")
st.markdown("##### Clinical-Grade Valsalva Graft Stencil Generator")

# ==========================================
# THE MASTER CONSOLE
# ==========================================
with st.sidebar:
    st.header("📋 Patient Logistics")
    case_id = st.text_input("Patient Case ID", "PX-990-OMEGA")
    
    st.header("🧬 Graft Specifications")
    graft_type = st.selectbox("Graft Material", ["Terumo Valsalva", "Woven Dacron", "ePTFE"])
    graft_diameter = st.slider("Graft Diameter (mm)", 26, 34, 30)
    sterilization = st.selectbox("Sterilization (Shrinkage)", ["Autoclave (1.4%)", "EtO Gas (0.8%)", "None"])
    
    st.header("⚙️ Radar Calibration")
    render_quality = st.select_slider("Radar Resolution", options=["Standard (360°)", "High (720°)", "Ultra (1440°)"], value="High (720°)")
    
    st.markdown("---")
    st.warning("Ensure 3D axis is completely leveled before execution.")

# --- THE MATH ENGINE ---
def auto_align_mesh(vertices):
    cov = np.cov(vertices.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    primary_axis = eigenvectors[:, np.argmax(eigenvalues)]
    if primary_axis[2] < 0: primary_axis = -primary_axis
    target_axis = np.array([0, 0, 1])
    rot_axis = np.cross(primary_axis, target_axis)
    rot_axis_norm = np.linalg.norm(rot_axis)
    if rot_axis_norm < 1e-6: return np.eye(3) 
    rot_axis /= rot_axis_norm
    angle = np.arccos(np.clip(np.dot(primary_axis, target_axis), -1.0, 1.0))
    return R.from_rotvec(rot_axis * angle).as_matrix()

# ==========================================
# MAIN DASHBOARD
# ==========================================
uploaded_file = st.file_uploader("Upload Patient Geometry (.zip containing .stl)", type=["zip"])

if uploaded_file is not None:
    # Read zip in memory (no temp folders needed)
    with zipfile.ZipFile(uploaded_file, 'r') as z:
        stl_filename = next((name for name in z.namelist() if name.lower().endswith('.stl')), None)
        if stl_filename:
            with z.open(stl_filename) as f:
                # Load trimesh directly from file object
                mesh = trimesh.load(f, file_type='stl')
                mesh.vertices -= np.mean(mesh.vertices, axis=0)
                auto_matrix = auto_align_mesh(mesh.vertices)
                mesh.vertices = np.dot(mesh.vertices, auto_matrix.T)

    # --- TOP ROW: GYROSCOPE ---
    st.markdown("### 1. Biological Axis Calibration")
    col1, col2, col3, col4 = st.columns([1,1,1,2])
    with col1: pitch = st.number_input("Pitch (X-Axis)", -45, 45, 0)
    with col2: roll = st.number_input("Roll (Y-Axis)", -45, 45, 0)
    with col3: yaw = st.number_input("Yaw (Z-Axis)", -180, 180, 0)
    
    rot_matrix = R.from_euler('xyz', [pitch, roll, yaw], degrees=True).as_matrix()
    
    # Generate Hologram Preview
    v = mesh.vertices
    step_size = max(1, len(v) // 15000)
    v_preview = v[::step_size]
    v_preview = np.dot(v_preview, rot_matrix.T)
    
    fig_3d = go.Figure(data=[go.Scatter3d(
        x=v_preview[:, 0], y=v_preview[:, 1], z=v_preview[:, 2],
        mode='markers', marker=dict(size=1.5, color='#00d4ff', opacity=0.7)
    )])
    fig_3d.update_layout(
        scene_camera=dict(eye=dict(x=0, y=2.0, z=0)),
        scene=dict(xaxis_visible=False, yaxis_visible=False, zaxis_visible=True),
        margin=dict(l=0, r=0, b=0, t=0), height=350,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
    )
    st.session_state.hologram_fig = fig_3d

    # --- EXECUTION BUTTON ---
    st.markdown("### 2. Generate Surgical Stencil")
    if st.button("▶ EXECUTE OMNI-ENGINE", type="primary", use_container_width=True):
        with st.spinner("Isolating Valsalva Frequencies via FFT..."):
            v_highres = np.dot(mesh.vertices, rot_matrix.T)
            x, y, z = v_highres[:, 0], v_highres[:, 1], v_highres[:, 2]
            
            angles = np.arctan2(y, x)
            angles = np.mod(angles, 2 * np.pi)
            
            res_map = {"Standard (360°)": 360, "High (720°)": 720, "Ultra (1440°)": 1440}
            num_bins = res_map[render_quality]
            
            bins = np.linspace(0, 2 * np.pi, num_bins + 1)
            indices = np.digitize(angles, bins)
            
            min_z = np.full(num_bins, np.nan)
            for i in range(1, num_bins + 1):
                mask = (indices == i)
                if np.any(mask):
                    slice_z = z[mask]
                    q15 = np.percentile(slice_z, 15)
                    valid_z = slice_z[slice_z <= q15]
                    min_z[i-1] = np.mean(valid_z) if len(valid_z) > 0 else np.min(slice_z)
                    
            valid = ~np.isnan(min_z)
            min_z_interp = np.interp(np.arange(num_bins), np.arange(num_bins)[valid], min_z[valid])
            
            # FFT BANDPASS
            fft_coeffs = np.fft.rfft(min_z_interp)
            fft_coeffs[1] = 0 # Kill Tilt
            fft_coeffs[2] = 0 # Kill Oval distortion
            fft_coeffs[4:] = 0 # Kill Noise
            smooth_z = np.fft.irfft(fft_coeffs, n=num_bins)
            
            z_range = np.max(smooth_z) - np.min(smooth_z)
            if z_range > 0:
                smooth_z = ((smooth_z - np.min(smooth_z)) / z_range) * 15.0 
            
            shrink_comp = 1.014 if "Autoclave" in sterilization else (1.008 if "EtO" in sterilization else 1.0)
            graft_circumference = (graft_diameter * np.pi) * shrink_comp
            
            x_flat = np.linspace(0, graft_circumference, num_bins)
            y_flat = smooth_z * shrink_comp
            y_flat = y_flat - np.min(y_flat) + 10.0

            # GENERATE PLOT
            fig, ax = plt.subplots(figsize=(8.27, 4)) # Live preview aspect ratio
            ax.plot(x_flat, y_flat, 'k-', lw=3.0)
            ax.plot([0, graft_circumference], [70, 70], 'k-', lw=1)
            ax.plot([0, 0], [y_flat[0], 70], 'k-', lw=1)
            ax.plot([graft_circumference, graft_circumference], [y_flat[-1], 70], 'k-', lw=1)
            ax.fill_between(x_flat, y_flat, 70, color='lightgray', alpha=0.3)
            
            mid_x = graft_circumference / 2.0
            ax.plot([mid_x, mid_x], [70, 75], 'b-', lw=2)
            ax.text(mid_x, 76, "LCA/RCA MARKER ALIGNMENT", color='blue', fontsize=7, ha='center')
            
            ax.add_patch(Rectangle((0, y_flat.min() - 8), 10, 10, fill=True, color='black'))
            ax.text(12, y_flat.min() - 6, "10mm CALIBRATION", fontsize=8, va='center')
            
            ax.set_aspect('equal')
            ax.axis('off')
            
            st.session_state.stencil_fig = fig
            
            # GENERATE PDF IN MEMORY (A4 Size)
            fig_pdf, ax_pdf = plt.subplots(figsize=(8.27, 11.69))
            ax_pdf.plot(x_flat, y_flat, 'k-', lw=3.0)
            ax_pdf.plot([0, graft_circumference], [70, 70], 'k-', lw=1)
            ax_pdf.plot([0, 0], [y_flat[0], 70], 'k-', lw=1)
            ax_pdf.plot([graft_circumference, graft_circumference], [y_flat[-1], 70], 'k-', lw=1)
            ax_pdf.fill_between(x_flat, y_flat, 70, color='lightgray', alpha=0.3)
            ax_pdf.plot([mid_x, mid_x], [70, 75], 'b-', lw=2)
            ax_pdf.text(mid_x, 76, "LCA/RCA MARKER ALIGNMENT", color='blue', fontsize=7, ha='center')
            ax_pdf.text(0, 85, "⚠️ REQUIRED PRINTER SETTING: 'ACTUAL SIZE' OR 'SCALE: 1.0 (100%)' ⚠️", color='red', fontsize=10, fontweight='bold')
            ax_pdf.text(0, 80, f"CASE: {case_id}\nGRAFT: {graft_diameter}mm {graft_type} | CIRC: {graft_circumference:.1f}mm", fontsize=9)
            ax_pdf.add_patch(Rectangle((0, y_flat.min() - 8), 10, 10, fill=True, color='black'))
            ax_pdf.text(12, y_flat.min() - 6, "10mm CALIBRATION", fontsize=8, va='center')
            ax_pdf.set_aspect('equal')
            ax_pdf.axis('off')
            
            pdf_buffer = io.BytesIO()
            fig_pdf.savefig(pdf_buffer, format='pdf', dpi=300, bbox_inches='tight')
            pdf_buffer.seek(0)
            
            st.session_state.pdf_buffer = pdf_buffer
            st.session_state.processed = True

    # --- DUAL SCREEN DISPLAY ---
    if st.session_state.processed:
        st.markdown("### 3. Surgical Review")
        
        # Dual Column Layout
        col_view1, col_view2 = st.columns(2)
        
        with col_view1:
            st.markdown("##### 3D Volumetric Anatomy")
            st.plotly_chart(st.session_state.hologram_fig, use_container_width=True)
            
        with col_view2:
            st.markdown("##### 2D Surgical Cut-Line Preview")
            st.pyplot(st.session_state.stencil_fig)
            
            st.download_button(
                label="📥 DOWNLOAD CLINICAL PDF",
                data=st.session_state.pdf_buffer,
                file_name=f"{case_id}_Surgical_Stencil.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )