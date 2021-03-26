from calculate_vectors_tibetan import calculate_vectors_folder

calculate_vectors_folder("/home/basti/data/tibetan/tsv/")

#populate_index("/mnt/data/tibetan/extract/")
#words = pickle.load( open( "/mnt2/skt2tib-data/tibwords.p", "rb" ) )
# sumvectordata = h5py.File('/mnt2/skt2tib-data/tibsumvectors.h5', 'r')
# sumvectors = sumvectordata.get('tibsumvectors')[:]
# index = faiss.IndexHNSWFlat(100, 32)
# #index = faiss.index_factory(100, "OPQ64_128,IVF262144_HNSW32,PQ32") # this is a compressed index
# index.verbose = True
# faiss.normalize_L2(sumvectors)
# index.train(sumvectors)
# index.add(sumvectors)
# print("Writing Index")
# faiss.write_index(index, "/mnt2/vectordata/tibvectors.idx")

# faiss.normalize_L2(sumvectors)
# index = faiss.IndexHNSWFlat(100, 32)
# index = faiss.index_factory(100, "OPQ64_128,IVF262144_HNSW32,PQ32") # this is a compressed index
# index.verbose = True
# faiss.normalize_L2(sumvectors)
# index.train(sumvectors)
# index.add(sumvectors)
# print("Writing Index")
#faiss.write_index(index, "/mnt2/vectordata/tibvectors.idx")

# faiss.normalize_L2(sumvectors)
# index = faiss.IndexHNSWSQ(100, faiss.ScalarQuantizer.QT_8bit, 32)
# index.verbose = True
# index.train(sumvectors)
# index.add(sumvectors)
# print("Writing Index")
# faiss.write_index(index, "/mnt2/vectordata/tibvectors.idx")
# index = faiss.read_index("/mnt2/vectordata/tibvectors.idx")
# index.hnsw.efSearch=128
# # list_of_ids = list(range(len(sumvectors)))
# # index = nmslib.init(method='hnsw', space='cosinesimil')
# index = faiss.IndexHNSWSQ(100, faiss.ScalarQuantizer.QT_8bit, 16)
# print("Creating Index...")
# #sumvectors = np.array(sumvectors).astype('float32')
# index.verbose = True
# index.train(sumvectors)
# index.add(sumvectors)
# print("Writing Index")
# faiss.write_index(index, "/mnt2/vectordata/tibvectors.idx")

#index.addDataPointBatch(sumvectors,list_of_ids)

#index.createIndex({'post': 1}, print_progress=True)
#index.saveIndex('/mnt2/vectordata/tib-all.nms')

# index_path = '/mnt2/vectordata/tibvectors.idx'
# output_path = "/mnt/output_parallel/tibetan/raw/"
# calculation = calculate_all(words,index_path,output_path)
# calculation.process_all()
