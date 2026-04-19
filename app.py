import streamlit as st
import trimesh
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import zipfile
import tempfile
import os

st.set_page_config(page_title="Aortic Smart Cut Pro", layout="wide")
st.title("🫀 Smart Cut Pro: Phase 3 Biomechanical Engine")

# Sidebar for Clinical Parameters
st.sidebar.header("Clinical Parameters")
pressure = st.sidebar.slider("Systolic Blood Pressure (mmHg)", 90, 180, 120)
compliance = st.sidebar.slider("Graft Elasticity (Compliance %)", 0.0, 10.0, 5.0) / 100

st.info("Phase 3: Integrating Pressure-Strain Compensation & Material Anisotropy.")
uploaded_file = st.file_uploader("Upload Anonymized Zip", type=["zip"])

if uploaded_file is not None:
    if st.button("Run Phase 3 Simulation", type="primary"):
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
                with st.spinner("Calculating Pressure-Induced Deformation..."):
                    mesh = trimesh.load(stl_file)
                    vertices = mesh.vertices
                    center = vertices.mean(axis=0)
                    v_centered = vertices - center
                    
                    # Apply Pressure Compensation (Radial Expansion)
                    # Simple linear elastic model: Expansion = (Pressure/Baseline) * Compliance
                    pressure_ratio = pressure / 120.0
                    expansion_factor = 1 + (pressure_ratio * compliance)
                    
                    # Expand X and Y (Radial), keep Z (Longitudinal) stable
                    v_centered[:, 0] *= expansion_factor
                    v_centered[:, 1] *= expansion_factor
                    
                    # Convert to Advanced Coordinates
                    theta = np.arctan2(v_centered[:, 1], v_centered[:, 0])
                    r_local = np.sqrt(v_centered[:, 0]**2 + v_centered[:, 1]**2)
                    
                    # Phase 3 Output: Compensated Planar Projection
                    x_2d = theta * r_local
                    y_2d = v_centered[:, 2]
                    
                    # Strain Mapping
                    mean_r = np.mean(r_local)
                    strain_map = np.abs(r_local - mean_r) / mean_r

                # PDF Generation
                fig, ax = plt.subplots(figsize=(8.5, 11))
                scatter = ax.scatter(x_2d, y_2d, c=strain_map, cmap='magma', s=0.1)
                
                # Annotations & Scale
                ax.text(0, np.max(y_2d)+25, f"STENCIL: {pressure}mmHg COMPENSATED", fontsize=12, fontweight='bold', ha='center')
                ax.text(0, np.max(y_2d)+15, f"Material Compliance Applied: {compliance*100}%", fontsize=9, ha='center')
                
                scale_box = Rectangle((np.min(x_2d), np.min(y_2d)-10), 10, 10, linewidth=1, edgecolor='r', facecolor='none')
                ax.add_patch(scale_box)
                ax.set_aspect('equal')
                ax.axis('off')
                
                pdf_path = os.path.join(temp_dir, "surgical_stencil_p3.pdf")
                plt.savefig(pdf_path, dpi=600, bbox_inches='tight')

                st.success(f"Simulation Complete. Aorta expanded by {((expansion_factor-1)*100):.1f}% for pressure compensation.")
                
                with open(pdf_path, "rb") as f:
                    st.download_button("📄 Download Phase 3 PDF", f, "stencil_pro.pdf")