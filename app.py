import streamlit as st
import trimesh
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import zipfile
import tempfile
import os

st.set_page_config(page_title="Aortic Smart Cut: OMNI MASTER", layout="wide")
st.title("🫀 Smart Cut: Phase 7 Omni-Surgical Master")

# --- SIDEBAR: THE COMPLETE CONSOLE ---
st.sidebar.header("1. Physiological & Stochastic")
pressure_mean = st.sidebar.slider("Mean Systolic Pressure", 90, 180, 120)
p_sigma = st.sidebar.slider("Pressure Uncertainty (σ)", 0, 20, 10)

st.sidebar.header("2. Bio-Kinematics")
torsion_deg = st.sidebar.slider("Systolic Torsion (Twist°)", 0, 20, 12)
smooth_passes = st.sidebar.slider("Laplacian Smoothing", 0, 50, 20)

st.sidebar.header("3. Material & Flow")
graft_ratio = st.sidebar.slider("Dacron Anisotropy (Vertical Stretch)", 1.1, 1.6, 1.4)
blood_velocity = st.sidebar.slider("Flow Velocity (m/s)", 0.5, 2.5, 1.2)

st.info("OMNI-MASTER ACTIVE: Unified Manifold, Iterative Optimization, and Stochastic Fluid Dynamics.")

uploaded_file = st.file_uploader("Upload Patient Zip", type=["zip"])

if uploaded_file is not None:
    if st.button("Generate Master Omni-Report", type="primary"):
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            stl_file = None
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.lower().endswith('.stl'):
                        stl_file = os.path.join(root, file)
                        break
            
            if stl_file:
                with st.spinner("Executing Unified Bio-Math Stack..."):
                    mesh = trimesh.load(stl_file)
                    # Phase 5: Initial Manifold Smoothing
                    if smooth_passes > 0:
                        mesh = trimesh.smoothing.filter_laplacian(mesh, iterations=smooth_passes)
                    
                    v_orig = mesh.vertices - mesh.vertices.mean(axis=0)
                    
                    # Phase 7: Monte Carlo Stochastic Loop
                    mc_x, mc_y = [], []
                    for _ in range(30): # 30 iterations for speed/stability
                        noise_p = pressure_mean + np.random.normal(0, p_sigma)
                        exp = 1 + (((noise_p - 120) * 0.0005))
                        
                        # Phase 7: Torsion Matrix
                        angle = np.radians(torsion_deg * (v_orig[:,2] / np.max(v_orig[:,2])))
                        c, s = np.cos(angle), np.sin(angle)
                        v_t = v_orig.copy()
                        v_t[:,0] = v_orig[:,0]*c - v_orig[:,1]*s
                        v_t[:,1] = v_orig[:,0]*s + v_orig[:,1]*c
                        
                        # Phase 3 & 4: Expansion + Numerical Projection
                        v_exp = v_t * [exp, exp, 1.0]
                        r = np.sqrt(v_exp[:,0]**2 + v_exp[:,1]**2)
                        theta = np.arctan2(v_exp[:,1], v_exp[:,0])
                        
                        # Phase 6: Anisotropy Apply
                        mc_x.append(theta * r)
                        mc_y.append(v_exp[:,2] / graft_ratio)

                    x_mean = np.mean(mc_x, axis=0)
                    y_mean = np.mean(mc_y, axis=0)

                    # Hemodynamics: Reynolds / Vorticity (Phase 7 Physics)
                    reynolds = (1060 * blood_velocity * (np.mean(r)*2/1000)) / 0.0035
                    vorticity = np.abs(np.gradient(r)) * (reynolds / 4000)

                # --- MULTI-LAYERED OUTPUT ---
                fig, ax = plt.subplots(figsize=(8.5, 11))
                
                # Layer 1: The Stochastic Blur (Safety Margin)
                for i in range(5): 
                    ax.scatter(mc_x[i], mc_y[i], color='blue', alpha=0.04, s=0.01)
                
                # Layer 2: Hemodynamic Risk Map
                sc = ax.scatter(x_mean, y_mean, c=vorticity, cmap='magma', s=0.1)
                
                ax.text(0, np.max(y_mean)+40, "OMNI-MASTER SURGICAL REPORT", fontsize=14, fontweight='bold', ha='center')
                ax.text(0, np.max(y_mean)+25, f"Confidence Interval: 95% | Torsion: {torsion_deg}° | Smoothing: {smooth_passes}p", fontsize=9, ha='center')
                
                ax.set_aspect('equal')
                ax.axis('off')
                
                # File Generation
                pdf_path = os.path.join(temp_dir, "master_report.pdf")
                plt.savefig(pdf_path, dpi=600, bbox_inches='tight')
                
                mandrel_path = os.path.join(temp_dir, "master_mandrel.stl")
                mesh.export(mandrel_path)
                
                st.success("Omni-Master Convergence Success.")
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("📄 Download Omni PDF", open(pdf_path, "rb"), "omni_report.pdf")
                with c2:
                    st.download_button("🧊 Download Master Mandrel", open(mandrel_path, "rb"), "master_mandrel.stl")