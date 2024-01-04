from utils.local_alignment_new import get_aligned_offsets_efficient
from utils.local_alignment_new import get_aligned_offsets
import time
# texta = "thog ma dang tha ma med pa stong pa nyid kyis yongs su ma bzung / dor ba med pa stong pa nyid kyis yongs su ma bzung / rang bzhin stong pa nyid kyis yongs su ma bzung / chos thams cad stong pa nyid kyis yongs su ma bzung / rang gi mtshan nyid stong pa nyid kyis yongs su ma bzung / mi dmigs pa stong pa nyid kyis yongs su ma bzung / dngos po med pa stong pa nyid kyis yongs su ma bzung /"
# textb = "thog ma dang tha ma med pa stong pa nyid kyi phyir sa bdun pa dmigs su med do // dor ba med pa stong pa nyid kyi phyir sa bdun pa dmigs su med do // rang bzhin stong pa nyid kyi phyir sa bdun pa dmigs su med do // chos thams cad stong pa nyid kyi phyir sa bdun pa dmigs su med do // rang gi mtshan nyid stong pa nyid kyi phyir sa bdun pa dmigs su med do // mi dmigs pa stong pa nyid kyi phyir sa bdun pa dmigs su med do // dngos po med pa stong pa nyid kyi phyir sa bdun pa dmigs su med do //"
# texta = "rtse mo rnyed pa spu gu can // bcom ldan 'das kyis / dge slong gis shing gi mchil lham bcang bar mi bya'o // zhes gsungs nas de"
# textb = "de lta bas na dge slong gis shing gi mchil lham bcang bar mi bya'o // bcom ldan 'das kyis dge slong gis shing gi mchil lham bcang bar mi bya'o zhes gsungs pa dang /"
# texta = "mdo sde gzhan la bskal pa dang / bskal pa'i lhag mar spyod pa dag ni ma yin no // de ci'i phyir zhe na /"
# textb = "de'i phyir de la 'bad par bya ba ma yin no //"
time_before = time.time()
texta_beg, texta_end, textb_beg, textb_end, score = get_aligned_offsets_efficient(texta, textb, 400, "tib")
time_after = time.time()
print("Time elapsed: ", time_after - time_before)
time_before = time.time()
texta_beg, texta_end, textb_beg, textb_end, score = get_aligned_offsets(texta, textb, "tib")
time_after = time.time()
print("Time elapsed: ", time_after - time_before)


print(texta_beg, texta_end, textb_beg, textb_end, score)
print(texta[texta_beg:texta_end])
print(textb[textb_beg:textb_end])