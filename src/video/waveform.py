def build_waveform_filter(waveform_style: str, is_vertical: bool) -> str:
    """
    Sinh chuỗi filter FFmpeg để tạo sóng âm (Audio Waveform Visualizer).
    """
    if "Tắt" in waveform_style or not waveform_style:
        return ""

    wave_size = "820x75" if is_vertical else "1200x65"
    wave_overlay_y = "H-h-240" if is_vertical else "H-h-25"

    if "Equalizer" in waveform_style:
        return f"[1:a]showfreqs=s={wave_size}:mode=bar:ascale=log:fscale=log:colors=0x00ffff@0.85|0xffd700@0.85,format=yuva420p[wave];[0:v][wave]overlay=(W-w)/2:{wave_overlay_y}"
    elif "Mềm mại" in waveform_style:
        return f"[1:a]showwaves=s={wave_size}:mode=line:colors=0xffffff@0.80:scale=sqrt:draw=full,format=yuva420p[wave];[0:v][wave]overlay=(W-w)/2:{wave_overlay_y}"
    elif "Vàng" in waveform_style:
        return f"[1:a]showfreqs=s={wave_size}:mode=bar:ascale=log:fscale=log:colors=0xffd700@0.85|0xffffff@0.85,format=yuva420p[wave];[0:v][wave]overlay=(W-w)/2:{wave_overlay_y}"
    elif "Gradient" in waveform_style:
        return f"[1:a]showwaves=s={wave_size}:mode=p2p:colors=0x00d4ff@0.80|0x7928ca@0.80:scale=cbrt,format=yuva420p[wave];[0:v][wave]overlay=(W-w)/2:{wave_overlay_y}"

    return ""
