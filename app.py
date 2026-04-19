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
st.markdown("### Cloud Processing Engine (Live Math)")
st.markdown("---")

st.info("Upload an anonymized patient DICOM/STL package (.zip) to generate a custom template.")
uploaded_file = st.file_uploader("Upload Anonymized Zip", type=["zip"])

if uploaded_file is not None:
    if st.button("Run Smart Cut Engine", type="primary"):
        
        # Create a temporary secure folder in the cloud to process the files
        with tempfile.TemporaryDirectory() as temp_dir:
            
            with st.spinner("1. Extracting ZIP File..."):
                # Unzip the uploaded file
                with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
# Find the STL file even if it is hidden inside sub-folders
                stl_file = None
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.lower().endswith('.stl'):
                            stl_file = os.path.join(root, file)
                            break # Found it!
                    if stl_file:
                        break # Stop searching
                stl_file = None
                for file in os.listdir(temp_dir):
                    if file.lower().endswith('.stl'):
                        stl_file = os.path.join(temp_dir, file)
                        break
            
            if stl_file is None:
                st.error("Could not find an .stl file inside the zip. Please check your file.")
            else:
 with st.spinner("2. Running Biomechanical Phase 2 Math..."):
                    # THIS IS THE ADVANCED ALGORITHM
                    mesh = trimesh.load(stl_file)
                    vertices = mesh.vertices
                    
                    # 1. Spatial Normalization
                    center = vertices.mean(axis=0)
                    centered_vertices = vertices - center
                    x, y, z = centered_vertices[:, 0], centered_vertices[:, 1], centered_vertices[:, 2]
                    
                    # 2. Localized Cylindrical Coordinates (Accounting for Sinus Bulges)
                    theta = np.arctan2(y, x)
                    r_local = np.sqrt(x**2 + y**2)
                    
                    # 3. Biomechanical Arc-Length Expansion
                    x_2d = theta * r_local
                    y_2d = z
                    
                    # 4. Calculate Fabric Stretch (Stress Map)
                    # We measure how much each point stretches compared to the base tube
                    mean_r = np.mean(r_local)
                    stretch_factor = np.abs(r_local - mean_r)

                with st.spinner("3. Generating Advanced Surgical PDF..."):
                    # Generate the PDF with a Biomechanical Heat Map
                    fig, ax = plt.subplots(figsize=(8.5, 11))
                    
                    # Plot the points, coloring them based on the stretch_factor (Red = High Stretch)
                    scatter = ax.scatter(x_2d, y_2d, c=stretch_factor, cmap='coolwarm', s=0.1)
                    
                    # Add Scale Check
                    scale_box = Rectangle((np.min(x_2d), np.min(y_2d)-10), 10, 10, linewidth=1, edgecolor='r', facecolor='none')
                    ax.add_patch(scale_box)
                    ax.text(np.min(x_2d), np.min(y_2d)-15, "1cm SCALE CHECK", color='red', fontsize=8)
                    
                    # Clinical Annotations
                    ax.text(0, np.max(y_2d)+20, "ADVANCED BIOMECHANICAL STENCIL (PHASE 2)", fontsize=12, fontweight='bold', ha='center')
                    ax.text(0, np.max(y_2d)+10, "HEAT MAP: Red = High Fabric Stretch (Sinuses) | Blue = Low Stretch", fontsize=9, ha='center', color='gray')
                    
                    ax.set_aspect('equal')
                    ax.axis('off')
                    
                    pdf_path = os.path.join(temp_dir, "surgical_stencil.pdf")
                    plt.savefig(pdf_path, dpi=600, bbox_inches='tight')
                    
                    # Generate the Mandrel
                    mandrel_path = os.path.join(temp_dir, "patient_mandrel.stl")
                    mesh.export(mandrel_path)

                st.success("Mathematical Unwrapping Complete!")
                
                # Provide the files directly to the user for download
                st.markdown("### Surgical Assets Ready")
                col1, col2 = st.columns(2)
                
                with col1:
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button(
                            label="📄 Download 1:1 Scale PDF Stencil",
                            data=pdf_file,
                            file_name="surgical_stencil.pdf",
                            mime="application/pdf"
                        )
                with col2:
                    with open(mandrel_path, "rb") as stl_out:
                        st.download_button(
                            label="🧊 Download 3D Print Mandrel",
                            data=stl_out,
                            file_name="patient_mandrel.stl",
                            mime="model/stl"
                        )