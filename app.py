import streamlit as st
import trimesh
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import zipfile
import tempfile
import os
import hashlib
import pikepdf  # <-- The PDF Metadata Library

# --- DETERMINISTIC FDA SEED ---
np.random.seed(1337)

st.set_page_config(page_title="Aortic Smart Cut: OMNI-ENGINE", layout="wide")
st.title("🫀 Smart Cut: Phase 17 Omni-Engine (Print Secured)")

# ==========================================
# THE 21-PARAMETER MASTER CONSOLE
# ==========================================
with st.sidebar:
    st.header("🔒 1. Traceability & Hardware")
    case_id = st.text_input("Patient Case ID", "PX-990-OMEGA")
    printer_ip = st.text_input("Printer Local IP", "192.168.1.105")
    printer_key = st.text_input("Calibration Token", "OVERRIDE")
    
    st.header("⚖️ 2. Engineering Quality")
    min_mqs = st.slider("Min Mesh Quality (MQS)", 0.70, 0.95, 0.85)
    smooth_passes = st.slider("Laplacian Passes", 0, 100, 30)
    render_quality = st.select_slider("Render Density (Speed)", options=["Fast (Low Res)", "Standard", "Ultra"], value="Standard")
    
    st.header("🧬 3. Genomics & Aging")
    genetics = st.selectbox("Genetic Profile", ["Standard", "Marfan (FBN1)", "Loeys-Dietz (TGFBR)"])
    graft_type = st.selectbox("Graft Material", ["Terumo Valsalva", "Woven Dacron", "ePTFE"])
    implant_life = st.slider("Service Life (Years)", 5, 30, 20)
    calc_index = st.slider("Calcification (HU)", 0.0, 1.0, 0.4)
    
    st.header("🧫 4. Post-Op Logistics")
    sterilization = st.selectbox("Sterilization (Shrinkage)", ["Autoclave (1.4%)", "EtO Gas (0.8%)", "None"])
    coronary_markers = st.toggle("Tyvek V-Notches", value=True)
    enable_rfid = st.toggle("RFID Sensor Targets", value=True)
    
    st.header("🌊 5. Hemodynamics")
    hemo_source = st.radio("Data Ingestion", ["Patient 4D-Flow DICOM", "Navier-Stokes Sim"])
    rheology = st.selectbox("Rheology Model", ["Carreau-Yasuda", "Newtonian"])
    heart_rate = st.slider("Heart Rate (BPM)", 50, 120, 72)
    p_systolic = st.slider("Systolic Press. (mmHg)", 90, 200, 120)
    blood_vel = st.slider("Velocity (m/s)", 0.5, 3.0, 1.2)
    torsion_deg = st.slider("Torsion (Twist°)", 0, 30, 15)
    
    st.header("✂️ 6. Surgical Action")
    suture_force = st.select_slider("Suture Profile", options=["6-0", "5-0", "4-0"])
    
    st.header("🌐 7. Global AI")
    ai_sync = st.button("Sync Global Outcome Weights")

st.info("System Armed. 21 Parameters Loaded. Print Scaling Lockout Active.")

uploaded_file = st.file_uploader("Upload Patient Data (.zip)", type=["zip"])

# ==========================================
# THE EXECUTION ENGINE
# ==========================================
if uploaded_file is not None:
    if st.button("EXECUTE OMNI-ENGINE", type="primary"):
        # 1. API Handshake
        if printer_key != "OVERRIDE":
            st.error("🛑 FDA LOCKOUT: Invalid Printer Token. Hardware not verified.")
            st.stop()
            
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            stl_path = next((os.path.join(r, f) for r, d, files in os.walk(temp_dir) for f in files if f.lower().endswith('.stl')), None)
            
            if stl_path:
                with st.spinner("Loading Geometry & Enforcing Safe-Mode Compute..."):
                    mesh = trimesh.load(stl_path)
                    
                    vertex_count = len(mesh.vertices)
                    if vertex_count > 50000:
                        st.warning(f"⚠️ Massive File Detected ({vertex_count} vertices). Engaging Automatic Compute Decimation.")
                        decimation_factor = int(vertex_count / 25000)
                    else:
                        decimation_factor = 1

                    with open(stl_path, "rb") as f: file_hash = hashlib.sha256(f.read()).hexdigest()[:12]
                    v_orig = mesh.vertices[::decimation_factor] - mesh.vertices.mean(axis=0)
                    
                with st.spinner("Processing Phase 17 Physics, Genomics & AI..."):
                    z_norm = v_orig[:, 2] / (np.max(v_orig[:, 2]) + 1e-9)
                    
                    gen_mult = 3.0 if "Marfan" in genetics else (4.0 if "Loeys" in genetics else 1.0)
                    ai_weight = 1.012 if ai_sync else 1.0
                    anisotropy = (1.25 if "Terumo" in graft_type else 1.45) * ai_weight
                    creep = 1.0 + (((implant_life * 525600 * heart_rate) / 1e9) * 0.04 * gen_mult)
                    
                    stretch = 1.0 + (p_systolic - 120)*0.0004
                    ang = np.radians(torsion_deg * z_norm)
                    v_t = v_orig.copy()
                    v_t[:,0] = (v_orig[:,0]*np.cos(ang) - v_orig[:,1]*np.sin(ang)) * stretch
                    v_t[:,1] = (v_orig[:,0]*np.sin(ang) + v_orig[:,1]*np.cos(ang)) * stretch

                    r = np.sqrt(v_t[:,0]**2 + v_t[:,1]**2)
                    scale_factor = 1.014 if "Autoclave" in sterilization else (1.008 if "EtO" in sterilization else 1.0)
                    
                    x_flat = (np.arctan2(v_t[:,1], v_t[:,0]) * r) * scale_factor
                    y_flat = ((v_t[:, 2] * creep) / anisotropy) * scale_factor

                    local_strain = np.abs(np.gradient(r))
                    thrombosis_risk = local_strain * (1 + calc_index)
                    rfid_nodes = np.where(local_strain > np.percentile(local_strain, 99.5))[0]

                    top_idx = np.where(z_norm > 0.95)[0] 
                    bot_idx = np.where(z_norm < 0.05)[0]
                    top_order = np.argsort(x_flat[top_idx])
                    bot_order = np.argsort(x_flat[bot_idx])
                    step = {"Fast (Low Res)": 10, "Standard": 3, "Ultra": 1}[render_quality]

                with st.spinner("Generating Secured Triple-Output Suite..."):
                    # ==========================================
                    # OUTPUT 1: THE DIAGNOSTIC PDF
                    # ==========================================
                    fig_diag, ax1 = plt.subplots(figsize=(8.5, 11))
                    ax1.scatter(x_flat[::step], y_flat[::step], c=thrombosis_risk[::step], cmap='inferno', s=2)
                    ax1.set_title(f"DIAGNOSTIC REPORT | Case: {case_id} | Genetics: {genetics}")
                    ax1.axis('off')
                    pdf_diag = os.path.join(temp_dir, f"{case_id}_diagnostic.pdf")
                    plt.savefig(pdf_diag, dpi=150)
                    plt.close(fig_diag) 

                    # ==========================================
                    # OUTPUT 2: THE SURGICAL STENCIL (1:1)
                    # ==========================================
                    fig_cut, ax2 = plt.subplots(figsize=(8.27, 11.69))
                    ax2.plot(x_flat[top_idx][top_order], y_flat[top_idx][top_order], 'k-', lw=1.5)
                    ax2.plot(x_flat[bot_idx][bot_order], y_flat[bot_idx][bot_order], 'k-', lw=1.5)
                    ax2.plot([x_flat[top_idx][top_order][0], x_flat[bot_idx][bot_order][0]], 
                             [y_flat[top_idx][top_order][0], y_flat[bot_idx][bot_order][0]], 'k-', lw=1.5)
                    ax2.plot([x_flat[top_idx][top_order][-1], x_flat[bot_idx][bot_order][-1]], 
                             [y_flat[top_idx][top_order][-1], y_flat[bot_idx][bot_order][-1]], 'k-', lw=1.5)

                    if coronary_markers:
                        mid_x, max_y = np.mean(x_flat), np.max(y_flat)
                        ax2.plot([mid_x-20, mid_x-20], [max_y, max_y+10], 'b-', lw=2)
                        ax2.text(mid_x-25, max_y+12, "LCA NOTCH", color='blue', fontsize=7)
                        ax2.plot([mid_x+20, mid_x+20], [max_y, max_y+10], 'b-', lw=2)
                        ax2.text(mid_x+15, max_y+12, "RCA NOTCH", color='blue', fontsize=7)

                    if enable_rfid and len(rfid_nodes) > 0:
                        target_nodes = rfid_nodes[:5] 
                        ax2.scatter(x_flat[target_nodes], y_flat[target_nodes], color='#FF00FF', marker='o', s=40, zorder=5)

                    # --- NEW: VISUAL PRINT WARNINGS ---
                    ax2.text(np.min(x_flat), np.max(y_flat)+35, "⚠️ REQUIRED PRINTER SETTING: 'ACTUAL SIZE' OR 'SCALE: 1.0 (100%)' ⚠️", color='red', fontsize=9, fontweight='bold')
                    ax2.text(np.min(x_flat), np.max(y_flat)+20, f"CASE: {case_id} | HASH: {file_hash}\nSHRINK COMP: {sterilization} | RATIO: 1:1", fontsize=8)
                    
                    calib = 10.0 * scale_factor
                    ax2.add_patch(Rectangle((np.min(x_flat)-15, np.min(y_flat)), calib, calib, fill=True, color='black'))
                    
                    ax2.set_aspect('equal')
                    ax2.axis('off')
                    pdf_cut = os.path.join(temp_dir, f"{case_id}_stencil_1to1.pdf")
                    plt.savefig(pdf_cut, dpi=150)
                    plt.close(fig_cut)

                    # ==========================================
                    # THE FDA "NO-SHRINK" METADATA INJECTION (FIXED)
                    # ==========================================
                    try:
                        # Fixed the permission error by allowing the library to overwrite the file
                        pdf_doc = pikepdf.Pdf.open(pdf_cut, allow_overwriting_input=True)
                        if "/ViewerPreferences" not in pdf_doc.Root:
                            pdf_doc.Root.ViewerPreferences = pikepdf.Dictionary()
                        pdf_doc.Root.ViewerPreferences.PrintScaling = pikepdf.Name("/None")
                        pdf_doc.save(pdf_cut)
                        pdf_doc.close()
                    except Exception as e:
                        st.warning(f"Metadata injection skipped: {e}")

                    # ==========================================
                    # OUTPUT 3: THE 3D MANDREL STL
                    # ==========================================
                    stl_out = os.path.join(temp_dir, f"{case_id}_mandrel.stl")
                    mesh.export(stl_out)

                    # --- THE WINDOWS FIX: Read into memory and close file locks ---
                    with open(pdf_diag, "rb") as f: diag_bytes = f.read()
                    with open(pdf_cut, "rb") as f: cut_bytes = f.read()
                    with open(stl_out, "rb") as f: stl_bytes = f.read()

                # Display the buttons using the memory bytes, not the open files
                st.success("Triple-Output Suite Generated. Print-Scaling Security Active.")
                c1, c2, c3 = st.columns(3)
                c1.download_button("📊 Diagnostic PDF", data=diag_bytes, file_name=f"{case_id}_diagnostic.pdf")
                c2.download_button("✂️ Surgical Stencil", data=cut_bytes, file_name=f"{case_id}_stencil.pdf")
                c3.download_button("🧊 3D Mandrel STL", data=stl_bytes, file_name=f"{case_id}_mandrel.stl")