from sentence_transformers import SentenceTransformer, util
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')



while True:
    print("Enter a sentence 1: ")
    sentence1 = input()
    print("Enter a sentence 2: ")
    sentence2 = input()
    distance = util.pytorch_cos_sim(model.encode(sentence1), model.encode(sentence2))
    print("Sentence 1:", sentence1)
    print("Sentence 2:", sentence2)
    print("Similarity Score:", distance)