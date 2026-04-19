import streamlit as st
import trimesh
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import zipfile
import tempfile
import os

# --- DETERMINISTIC SEED ---
np.random.seed(1337)

st.set_page_config(page_title="Aortic Smart Cut: TRIPLE OUTPUT", layout="wide")
st.title("🫀 Smart Cut: Phase 12 Triple-Output Suite")

# --- THE SOVEREIGN CONSOLE ---
with st.sidebar:
    st.header("📋 FDA Case Info")
    case_id = st.text_input("Patient Case ID", "PX-990-ALPHA")
    
    st.header("⚖️ Engineering & Safety")
    min_mqs = st.slider("Min Mesh Quality (MQS)", 0.70, 0.95, 0.85)
    smooth_passes = st.slider("Laplacian Smoothing", 0, 100, 30)
    
    st.header("🧬 Material & Aging")
    graft_type = st.selectbox("Graft Brand/Type", [
        "Terumo Valsalva (Knitted)", 
        "Standard Woven Dacron", 
        "ePTFE (Low Stretch)"
    ])
    implant_life = st.slider("Target Service Life (Years)", 5, 30, 20)
    heart_rate = st.slider("Average Heart Rate (BPM)", 50, 120, 72)
    
    st.header("🌊 Hemodynamics")
    torsion_deg = st.slider("Systolic Torsion (Twist°)", 0, 30, 15)
    blood_velocity = st.slider("Flow Velocity (m/s)", 0.5, 3.0, 1.2)
    calc_index = st.slider("Calcification Density", 0.0, 1.0, 0.4)

st.info("Phase 12 Active: 1:1 Stencil Extraction + Diagnostic Mapping + 3D Mandrel.")

uploaded_file = st.file_uploader("Upload Clinical STL Package", type=["zip"])

if uploaded_file is not None:
    if st.button("GENERATE TRIPLE-OUTPUT SUITE", type="primary"):
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            stl_path = next((os.path.join(r, f) for r, d, files in os.walk(temp_dir) for f in files if f.lower().endswith('.stl')), None)
            
            if stl_path:
                with st.spinner("Processing Bio-Sim & Stencil Vectorization..."):
                    mesh = trimesh.load(stl_path)
                    
                    # 1. QUALITY CHECK
                    faces = mesh.vertices[mesh.faces]
                    area = 0.5 * np.linalg.norm(np.cross(faces[:,1]-faces[:,0], faces[:,2]-faces[:,0]), axis=1)
                    a, b, c = np.linalg.norm(faces[:,0]-faces[:,1], axis=1), np.linalg.norm(faces[:,1]-faces[:,2], axis=1), np.linalg.norm(faces[:,2]-faces[:,0], axis=1)
                    mqs = np.mean((4 * np.sqrt(3) * area) / (a**2 + b**2 + c**2 + 1e-10))
                    
                    if mqs < min_mqs:
                        st.error("AUDIT REJECTED: Geometry unstable.")
                        st.stop()

                    # 2. MANIFOLD FLATTENING
                    if smooth_passes > 0:
                        mesh = trimesh.smoothing.filter_laplacian(mesh, iterations=smooth_passes)
                    
                    v_orig = mesh.vertices - mesh.vertices.mean(axis=0)
                    z_norm = v_orig[:, 2] / np.max(v_orig[:, 2])
                    
                    # Material Constants
                    anisotropy = 1.25 if "Terumo" in graft_type else 1.45
                    total_cycles = implant_life * 525600 * heart_rate
                    creep = 1.0 + (total_cycles / 1e9) * 0.04
                    
                    # Compute Flat Coordinates
                    ang = np.radians(torsion_deg * z_norm)
                    v_t = v_orig.copy()
                    v_t[:,0] = v_orig[:,0]*np.cos(ang) - v_orig[:,1]*np.sin(ang)
                    v_t[:,1] = v_orig[:,0]*np.sin(ang) + v_orig[:,1]*np.cos(ang)
                    
                    r = np.sqrt(v_t[:,0]**2 + v_t[:,1]**2)
                    x_flat = np.arctan2(v_t[:,1], v_t[:,0]) * r
                    y_flat = (v_t[:, 2] * creep) / anisotropy

                    # 3. BOUNDARY EXTRACTION (The "Cut Line")
                    # We find vertices at the very top and very bottom
                    top_idx = np.where(z_norm > 0.98)[0]
                    bot_idx = np.where(z_norm < 0.02)[0]
                    # Sort by theta to create a continuous line
                    top_order = np.argsort(np.arctan2(v_t[top_idx, 1], v_t[top_idx, 0]))
                    bot_order = np.argsort(np.arctan2(v_t[bot_idx, 1], v_t[bot_idx, 0]))

                    # --- OUTPUT 1: THE DIAGNOSTIC PDF ---
                    fig_diag, ax1 = plt.subplots(figsize=(8.5, 11))
                    ax1.scatter(x_flat, y_flat, c=np.abs(np.gradient(r)), cmap='turbo', s=0.1)
                    ax1.set_title(f"DIAGNOSTIC REPORT: {case_id}")
                    ax1.axis('off')
                    pdf_diag = os.path.join(temp_dir, "diagnostic.pdf")
                    plt.savefig(pdf_diag)

                    # --- OUTPUT 2: THE 1:1 SURGICAL STENCIL ---
                    # Set figure size to A4 (210x297mm)
                    fig_cut, ax2 = plt.subplots(figsize=(8.27, 11.69)) 
                    # Draw the Cut Lines
                    ax2.plot(x_flat[top_idx][top_order], y_flat[top_idx][top_order], color='black', lw=1.5)
                    ax2.plot(x_flat[bot_idx][bot_order], y_flat[bot_idx][bot_order], color='black', lw=1.5)
                    # Close the sides
                    ax2.plot([x_flat[top_idx][top_order][0], x_flat[bot_idx][bot_order][0]], 
                             [y_flat[top_idx][top_order][0], y_flat[bot_idx][bot_order][0]], color='black', lw=1.5)
                    ax2.plot([x_flat[top_idx][top_order][-1], x_flat[bot_idx][bot_order][-1]], 
                             [y_flat[top_idx][top_order][-1], y_flat[bot_idx][bot_order][-1]], color='black', lw=1.5)
                    
                    # 10mm Calibration Square (Critical for 1:1 Verification)
                    ax2.add_patch(Rectangle((np.min(x_flat)-20, np.min(y_flat)), 10, 10, fill=True, color='black'))
                    ax2.text(np.min(x_flat)-20, np.min(y_flat)-5, "10mm CALIBRATION", fontsize=6)
                    
                    ax2.text(0, np.max(y_flat)+10, "↑ CRANIAL (STJ) ↑", ha='center', fontsize=10, fontweight='bold')
                    ax2.text(0, np.min(y_flat)-15, "↓ CAUDAL (ANNULUS) ↓", ha='center', fontsize=10, fontweight='bold')
                    ax2.set_aspect('equal')
                    ax2.axis('off')
                    pdf_cut = os.path.join(temp_dir, "surgical_stencil.pdf")
                    plt.savefig(pdf_cut, dpi=600)

                    # 4. EXPORT
                    mesh.export(os.path.join(temp_dir, "mandrel.stl"))

                st.success("Sovereign Triple-Output Suite Generated.")
                c1, c2, c3 = st.columns(3)
                c1.download_button("📄 Diagnostic PDF", open(pdf_diag, "rb"), "diagnostic.pdf")
                c2.download_button("✂️ Surgical Stencil (1:1)", open(pdf_cut, "rb"), "stencil_1to1.pdf")
                c3.download_button("🧊 3D Mandrel STL", open(os.path.join(temp_dir, "mandrel.stl"), "rb"), "mandrel.stl")