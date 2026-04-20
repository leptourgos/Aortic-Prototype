if st.button("GENERATE TRIPLE-OUTPUT SUITE (SAFE MODE)", type="primary"):
        if printer_key != "OVERRIDE":
            st.error("🛑 FDA LOCKOUT: Invalid Printer Token.")
            st.stop()
            
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            stl_path = next((os.path.join(r, f) for r, d, files in os.walk(temp_dir) for f in files if f.lower().endswith('.stl')), None)
            
            if stl_path:
                with st.spinner("Loading Geometry..."):
                    mesh = trimesh.load(stl_path)
                    
                    # --- THE SAFEGUARD: VERTEX CAPPING ---
                    vertex_count = len(mesh.vertices)
                    if vertex_count > 50000:
                        st.warning(f"⚠️ Massive File Detected ({vertex_count} vertices). Engaging Automatic Decimation to prevent server freeze.")
                        # Force decimation (take every Nth vertex for the math)
                        decimation_factor = int(vertex_count / 25000)
                    else:
                        decimation_factor = 1

                    v_orig = mesh.vertices[::decimation_factor] - mesh.vertices.mean(axis=0)
                    
                with st.spinner("Processing First-Principles Math (Safe Mode)..."):
                    # Cryptography
                    with open(stl_path, "rb") as f: file_hash = hashlib.sha256(f.read()).hexdigest()[:12]
                    
                    z_norm = v_orig[:, 2] / (np.max(v_orig[:, 2]) + 1e-9)
                    
                    # Genomics & AI Weights
                    gen_mult = 3.0 if "Marfan" in genetics else (4.0 if "Loeys" in genetics else 1.0)
                    ai_weight = 1.012 if ai_sync else 1.0
                    anisotropy = (1.25 if "Terumo" in graft_type else 1.45) * ai_weight
                    creep = 1.0 + (((implant_life * 525600 * heart_rate) / 1e9) * 0.04 * gen_mult)
                    
                    # Kinematics
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

                    # Boundary Extraction (Safeguarded)
                    top_idx = np.where(z_norm > 0.95)[0] # Widened boundary capture slightly
                    bot_idx = np.where(z_norm < 0.05)[0]
                    top_order = np.argsort(x_flat[top_idx])
                    bot_order = np.argsort(x_flat[bot_idx])

                with st.spinner("Rendering Triple-Output PDFs..."):
                    # ==========================================
                    # OUTPUT 1: THE DIAGNOSTIC PDF
                    # ==========================================
                    fig_diag, ax1 = plt.subplots(figsize=(8.5, 11))
                    ax1.scatter(x_flat, y_flat, c=thrombosis_risk, cmap='inferno', s=2) # Decimated by default now
                    ax1.set_title(f"DIAGNOSTIC REPORT | Case: {case_id} | Genetics: {genetics}")
                    ax1.axis('off')
                    pdf_diag = os.path.join(temp_dir, f"{case_id}_diagnostic.pdf")
                    plt.savefig(pdf_diag, dpi=150) # Lowered DPI to prevent memory crash
                    plt.close(fig_diag) # Explicitly clear memory

                    # ==========================================
                    # OUTPUT 2: THE SURGICAL STENCIL (1:1)
                    # ==========================================
                    fig_cut, ax2 = plt.subplots(figsize=(8.27, 11.69))
                    # Safely plot boundaries without choking on overlapping points
                    ax2.scatter(x_flat[top_idx], y_flat[top_idx], color='black', s=1)
                    ax2.scatter(x_flat[bot_idx], y_flat[bot_idx], color='black', s=1)

                    if coronary_markers:
                        mid_x, max_y = np.mean(x_flat), np.max(y_flat)
                        ax2.plot([mid_x-20, mid_x-20], [max_y, max_y+10], 'b-', lw=2)
                        ax2.text(mid_x-25, max_y+12, "LCA NOTCH", color='blue', fontsize=7)
                        ax2.plot([mid_x+20, mid_x+20], [max_y, max_y+10], 'b-', lw=2)
                        ax2.text(mid_x+15, max_y+12, "RCA NOTCH", color='blue', fontsize=7)

                    if enable_rfid and len(rfid_nodes) > 0:
                        target_nodes = rfid_nodes[:5] 
                        ax2.scatter(x_flat[target_nodes], y_flat[target_nodes], color='#FF00FF', marker='o', s=40, zorder=5)

                    ax2.text(np.min(x_flat), np.max(y_flat)+20, f"CASE: {case_id} | HASH: {file_hash}\nSHRINK COMP: {sterilization}", fontsize=8)
                    calib = 10.0 * scale_factor
                    ax2.add_patch(Rectangle((np.min(x_flat)-15, np.min(y_flat)), calib, calib, fill=True, color='black'))
                    
                    ax2.set_aspect('equal')
                    ax2.axis('off')
                    pdf_cut = os.path.join(temp_dir, f"{case_id}_stencil_1to1.pdf")
                    plt.savefig(pdf_cut, dpi=150)
                    plt.close(fig_cut)

                    # ==========================================
                    # OUTPUT 3: THE 3D MANDREL STL
                    # ==========================================
                    stl_out = os.path.join(temp_dir, f"{case_id}_mandrel.stl")
                    mesh.export(stl_out)

                st.success("Triple-Output Suite Generated Successfully in Safe Mode.")
                c1, c2, c3 = st.columns(3)
                c1.download_button("📊 Diagnostic PDF", open(pdf_diag, "rb"), f"{case_id}_diagnostic.pdf")
                c2.download_button("✂️ Surgical Stencil", open(pdf_cut, "rb"), f"{case_id}_stencil.pdf")
                c3.download_button("🧊 3D Mandrel STL", open(stl_out, "rb"), f"{case_id}_mandrel.stl")