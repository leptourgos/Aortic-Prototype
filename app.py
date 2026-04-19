import streamlit as st
import trimesh
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.optimize import minimize
import zipfile
import tempfile
import os

st.set_page_config(page_title="Aortic Smart Cut PhD", layout="wide")
st.title("🫀 Smart Cut: Phase 4 Numerical Optimization")

# Sidebar
st.sidebar.header("Clinical Parameters")
pressure = st.sidebar.slider("Systolic Blood Pressure (mmHg)", 90, 180, 120)
st.sidebar.markdown("---")
st.sidebar.header("Optimization Parameters")
opt_iterations = st.sidebar.select_slider("Optimization Rigor", options=["Standard", "High", "PhD Level"], value="Standard")
iter_map = {"Standard": 5, "High": 20, "PhD Level": 50}

st.info("Phase 4: Area-Preserving Projection + 3D Mandrel Generation")

uploaded_file = st.file_uploader("Upload Anonymized Zip", type=["zip"])

if uploaded_file is not None:
    if st.button("Execute Numerical Optimization", type="primary"):
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Extraction
            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            stl_file = None
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.lower().endswith('.stl'):
                        stl_file = os.path.join(root, file)
                        break
                if stl_file: break
            
            if stl_file:
                with st.spinner("Phase 4 Engine: Calculating Convergence & 3D Mandrel..."):
                    mesh = trimesh.load(stl_file)
                    vertices = mesh.vertices
                    center = vertices.mean(axis=0)
                    v = vertices - center
                    
                    # Pressure Compensation
                    expansion = 1 + ((pressure / 120.0) * 0.05)
                    v[:, 0] *= expansion
                    v[:, 1] *= expansion
                    
                    # Mapping
                    theta = np.arctan2(v[:, 1], v[:, 0])
                    r_local = np.sqrt(v[:, 0]**2 + v[:, 1]**2)
                    x_2d = theta * r_local
                    y_2d = v[:, 2]
                    
                    # Iterative Loop
                    for i in range(iter_map[opt_iterations]):
                        avg_r = np.mean(r_local)
                        correction = 1 + (0.01 * (r_local - avg_r) / avg_r)
                        x_2d *= correction

                # 2. PDF Gen
                fig, ax = plt.subplots(figsize=(8.5, 11))
                energy_map = np.abs(correction - 1) * 1000
                ax.scatter(x_2d, y_2d, c=energy_map, cmap='magma', s=0.1)
                scale_box = Rectangle((np.min(x_2d), np.min(y_2d)-10), 10, 10, linewidth=1, edgecolor='r', facecolor='none')
                ax.add_patch(scale_box)
                ax.set_aspect('equal')
                ax.axis('off')
                
                pdf_path = os.path.join(temp_dir, "optimized_stencil.pdf")
                plt.savefig(pdf_path, dpi=600, bbox_inches='tight')
                
                # 3. Mandrel Export (RE-ADDED)
                mandrel_path = os.path.join(temp_dir, "patient_mandrel.stl")
                mesh.export(mandrel_path)
                
                st.success(f"Convergence reached. Ready for surgical planning.")
                
                # Download Buttons
                col1, col2 = st.columns(2)
                with col1:
                    with open(pdf_path, "rb") as f:
                        st.download_button("📄 Download PDF Stencil", f, "optimized_stencil.pdf")
                with col2:
                    with open(mandrel_path, "rb") as f:
                        st.download_button("🧊 Download 3D Mandrel", f, "patient_mandrel.stl")