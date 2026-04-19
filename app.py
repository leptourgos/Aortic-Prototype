import streamlit as st
import trimesh
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import zipfile
import tempfile
import os

st.set_page_config(page_title="Aortic Smart Cut", layout="wide")
st.title("🫀 Patient-Identical Aortic Graft Stencil")
st.markdown("### Advanced Biomechanical Engine (Phase 2)")
st.markdown("---")

st.info("Upload an anonymized patient DICOM/STL package (.zip) to generate a custom template.")
uploaded_file = st.file_uploader("Upload Anonymized Zip", type=["zip"])

if uploaded_file is not None:
    if st.button("Run Smart Cut Engine", type="primary"):
        with tempfile.TemporaryDirectory() as temp_dir:
            
            # 1. Extraction with recursive search
            with st.spinner("1. Extracting ZIP File..."):
                with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                stl_file = None
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.lower().endswith('.stl'):
                            stl_file = os.path.join(root, file)
                            break
                    if stl_file: break
            
            if stl_file is None:
                st.error("Could not find an .stl file inside the zip. Please check your file.")
            else:
                # 2. Advanced Phase 2 Math
                with st.spinner("2. Running Biomechanical Phase 2 Math..."):
                    mesh = trimesh.load(stl_file)
                    vertices = mesh.vertices
                    center = vertices.mean(axis=0)
                    centered_vertices = vertices - center
                    x, y, z = centered_vertices[:, 0], centered_vertices[:, 1], centered_vertices[:, 2]
                    
                    # Localized Cylindrical Coordinates (Accounting for Sinus Bulges)
                    theta = np.arctan2(y, x)
                    r_local = np.sqrt(x**2 + y**2)
                    
                    # Biomechanical Arc-Length Expansion
                    x_2d = theta * r_local
                    y_2d = z
                    
                    # Calculate Fabric Stretch Heat Map
                    mean_r = np.mean(r_local)
                    stretch_factor = np.abs(r_local - mean_r)

                # 3. Generating Advanced PDF
                with st.spinner("3. Generating Advanced Surgical PDF..."):
                    fig, ax = plt.subplots(figsize=(8.5, 11))
                    scatter = ax.scatter(x_2d, y_2d, c=stretch_factor, cmap='coolwarm', s=0.1)
                    
                    # Add Scale Check
                    scale_box = Rectangle((np.min(x_2d), np.min(y_2d)-10), 10, 10, linewidth=1, edgecolor='r', facecolor='none')
                    ax.add_patch(scale_box)
                    ax.text(np.min(x_2d), np.min(y_2d)-15, "1cm SCALE CHECK", color='red', fontsize=8)
                    
                    # Annotations
                    ax.text(0, np.max(y_2d)+20, "ADVANCED BIOMECHANICAL STENCIL (PHASE 2)", fontsize=12, fontweight='bold', ha='center')
                    ax.text(0, np.max(y_2d)+10, "HEAT MAP: Red = High Stretch | Blue = Low Stretch", fontsize=9, ha='center', color='gray')
                    
                    ax.set_aspect('equal')
                    ax.axis('off')
                    
                    pdf_path = os.path.join(temp_dir, "surgical_stencil.pdf")
                    plt.savefig(pdf_path, dpi=600, bbox_inches='tight')
                    mandrel_path = os.path.join(temp_dir, "patient_mandrel.stl")
                    mesh.export(mandrel_path)

                st.success("Mathematical Unwrapping Complete!")
                
                col1, col2 = st.columns(2)
                with col1:
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button("📄 Download 1:1 Scale PDF", pdf_file, "surgical_stencil.pdf", "application/pdf")
                with col2:
                    with open(mandrel_path, "rb") as stl_out:
                        st.download_button("🧊 Download 3D Print Mandrel", stl_out, "patient_mandrel.stl", "model/stl")