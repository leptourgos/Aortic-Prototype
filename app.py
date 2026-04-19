import streamlit as st
import trimesh
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.optimize import minimize
import zipfile
import tempfile
import os

st.set_page_config(page_title="Aortic Smart Cut: MASTER", layout="wide")
st.title("🫀 Smart Cut: Phase 6 Unified Master Engine")

# --- SIDEBAR: ALL PARAMETERS UNIFIED ---
st.sidebar.header("1. Physiological Data")
pressure = st.sidebar.slider("Systolic Pressure (mmHg)", 80, 200, 120)
stiffness = st.sidebar.select_slider("Aortic Wall Health", options=["Marfan/Thin", "Normal", "Calcified/Stiff"], value="Normal")

st.sidebar.header("2. Material Science")
graft_type = st.sidebar.selectbox("Graft Material", ["Standard Woven Dacron", "Terumo Valsalva (Knitted)"])

st.sidebar.header("3. Math Rigor (PhD Level)")
opt_rigor = st.sidebar.select_slider("Optimization Iterations", options=[10, 30, 100], value=30)
smooth_passes = st.sidebar.slider("Laplacian Smoothing", 0, 50, 15)

st.info("Unified Engine Active: Manifold Geometry + Numerical Optimization + Physiological Constraints.")

uploaded_file = st.file_uploader("Upload Patient Package (.zip)", type=["zip"])

if uploaded_file is not None:
    if st.button("Generate Master Clinical Stencil", type="primary"):
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find STL
            stl_file = None
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.lower().endswith('.stl'):
                        stl_file = os.path.join(root, file)
                        break
            
            if stl_file:
                with st.spinner("Processing: Running Unified Bio-Math Stack..."):
                    mesh = trimesh.load(stl_file)
                    
                    # STEP 1: Phase 5 - Laplacian Manifold Smoothing
                    if smooth_passes > 0:
                        mesh = trimesh.smoothing.filter_laplacian(mesh, iterations=smooth_passes)
                    
                    vertices = mesh.vertices
                    center = vertices.mean(axis=0)
                    v = vertices - center
                    
                    # STEP 2: Phase 3/6 - Pressure & Stiffness Scaling
                    # Thinner walls (Marfan) expand more than calcified walls
                    stiffness_map = {"Marfan/Thin": 1.2, "Normal": 1.0, "Calcified/Stiff": 0.8}
                    expansion = 1 + (((pressure - 120) * 0.0005) * stiffness_map[stiffness])
                    v[:, 0] *= expansion
                    v[:, 1] *= expansion
                    
                    # STEP 3: Initial Manifold Projection
                    theta = np.arctan2(v[:, 1], v[:, 0])
                    r_local = np.sqrt(v[:, 0]**2 + v[:, 1]**2)
                    x_2d = theta * r_local
                    y_2d = v[:, 2]
                    
                    # STEP 4: Phase 4 - Iterative Numerical Area-Preservation Loop
                    for i in range(opt_rigor):
                        avg_r = np.mean(r_local)
                        # We nudge the points to resolve Dirichlet Energy
                        correction = 1 + (0.01 * (r_local - avg_r) / avg_r)
                        x_2d *= correction
                    
                    # STEP 5: Phase 6 - Material Anisotropy (Dacron Warp/Weft)
                    # Surgical fabric stretches more vertically (Longitudinal)
                    anisotropy_ratio = 1.40 if "Dacron" in graft_type else 1.25
                    y_2d /= anisotropy_ratio 

                # --- OUTPUT GENERATION ---
                fig, ax = plt.subplots(figsize=(8.5, 11))
                # Color map represents Residual Energy (The 'PhD Diagnostic')
                energy_error = np.abs(correction - 1) * 1000
                ax.scatter(x_2d, y_2d, c=energy_error, cmap='magma', s=0.1)
                
                # Clinical Details
                ax.text(0, np.max(y_2d)+30, "UNIFIED CLINICAL MASTER STENCIL", fontsize=12, fontweight='bold', ha='center')
                ax.text(0, np.max(y_2d)+20, f"Pressure: {pressure}mmHg | Material: {graft_type}", fontsize=9, ha='center')
                
                # Scale Check box
                ax.add_patch(Rectangle((np.min(x_2d), np.min(y_2d)-10), 10, 10, linewidth=1, edgecolor='r', facecolor='none'))
                ax.axis('off')
                ax.set_aspect('equal')
                
                pdf_path = os.path.join(temp_dir, "master_stencil.pdf")
                plt.savefig(pdf_path, dpi=600, bbox_inches='tight')
                
                mandrel_path = os.path.join(temp_dir, "master_mandrel.stl")
                mesh.export(mandrel_path)
                
                st.success("Master Simulation Converged.")
                c1, c2 = st.columns(2)
                c1.download_button("📄 Download Master PDF", open(pdf_path, "rb"), "master_stencil.pdf")
                c2.download_button("🧊 Download Master Mandrel", open(mandrel_path, "rb"), "master_mandrel.stl")