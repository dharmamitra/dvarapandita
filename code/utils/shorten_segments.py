def shorten_segments(target_offset_beg,
                     target_offset_end,
                     inquiry_offset_beg,
                     inquiry_offset_end,                     
                     target_segtext,
                     target_segnr,
                     inquiry_segtext,
                     inquiry_segnr,
                     lang):
    acc = 0
    j = 0
    gap_len = 1
    if lang == "chn" or lang == "pli" or lang == "skt":
        gap_len = 0
    target_offset_end_last_segment = 0
    for ctarget in target_segtext:
        if acc + len(ctarget) +2  > target_offset_end:
            target_offset_end_last_segment = target_offset_end - acc
            break
        acc+= len(ctarget) + gap_len
        j += 1
    target_segtext = target_segtext[0:j+1]
    target_segnr = target_segnr[0:j+1]
    acc = 0
    j = 0 
    inquiry_offset_end_last_segment = 0 
    for ctarget in inquiry_segtext:
        if acc + len(ctarget) +2 > inquiry_offset_end:
            inquiry_offset_end_last_segment = inquiry_offset_end - acc
            break
        acc+= len(ctarget) + gap_len
        j += 1
    inquiry_segnr = inquiry_segnr[0:j+1]
    inquiry_segtext = inquiry_segtext[0:j+1]
    acc = 0
    j = 0 
    target_offset_beg_final = 0
    for ctarget in target_segtext:
        if acc + len(ctarget) +2  > target_offset_beg:
            target_offset_beg_final = target_offset_beg - acc
            break
        acc+= len(ctarget) + gap_len
        j += 1
    target_segtext = target_segtext[j:]
    target_segnr = target_segnr[j:]            
    acc = 0
    j = 0 
    inquiry_offset_beg_final = 0 
    for ctarget in inquiry_segtext:
        if acc + len(ctarget) + 2 > inquiry_offset_beg:
            inquiry_offset_beg_final = inquiry_offset_beg - acc
            break
        acc+= len(ctarget) + gap_len
        j += 1
    inquiry_segnr = inquiry_segnr[j:]
    inquiry_segtext = inquiry_segtext[j:]
    return [target_offset_beg_final,target_offset_end_last_segment,inquiry_offset_beg_final,inquiry_offset_end_last_segment,target_segtext,target_segnr,inquiry_segtext,inquiry_segnr]
