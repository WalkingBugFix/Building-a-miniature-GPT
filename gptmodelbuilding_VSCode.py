# -*- coding: utf-8 -*-
"""GPTmodelbuilding.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1O_4566ZLbRFSmNRCt9Z2rdUc_NNzjJ6c
"""

# We always start with a dataset to train on. Let's download the reddit jokes dataset
!wget https://raw.githubusercontent.com/taivop/joke-dataset/refs/heads/master/reddit_jokes.json
import json
# read it in to inspect it
with open('reddit_jokes.json.4', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Peek at the first joke
print("First joke entry:")
print(json.dumps(data[0], indent=2))

# Check the type and length
print(f"Type of data: {type(data)}")
print(f"Number of jokes: {len(data)}")

# combining the separate dictionaries for each joke into strings
lines = []
for joke in data:
    if 'title' in joke and 'body' in joke:
        title = joke['title'].strip()
        body = joke['body'].strip()
        if title and body:
            lines.extend([title, body, ''])  # add a blank line between jokes

# checking the first 1000 characters of the dataset
print(data[:1000])

# Step 2: Sample first 50,000 lines
max_lines = 50000
sampled_lines = lines[:max_lines]

# Step 3: Join into a single text
sampled_text = '\n'.join(sampled_lines)

# getting the unique characters in the data to define our vocabulary size
chars = sorted(list(set(sampled_text)))
vocab_size= len(chars)
print(''.join(chars))
print(vocab_size)

# create a mapping from characters to integers
stoi = {ch:i for i, ch in enumerate(chars)}
itos = {i:ch for i, ch in enumerate(chars)}
encode = lambda s: [stoi[c] for c in s] # encoder takes an input string and gives an output of a list of integers
decode = lambda l: ''.join([itos[i] for i in l]) # decoder takes a list of integers and gives an ouput of a string

# here we have defined our tokenizer
# lets check how it words
print(encode('hi there'))
print(decode(encode('hi there')))

# we will now use to the tokenizer to encode our training data
import torch
data = torch.tensor(encode(sampled_text), dtype=torch.long)
print(data.shape, data.dtype)
print(data[:1000]) # this will be our input to our GPT model

# splitting our processed data into training and validation sets
n = int(0.9*len(data)) # assigning 90% to the training data, and rest will be validation data
train_data = data[:n]
val_data = data[n:]

# defining the block size of data to input (we will give blocks as input because it will be very computationally expensive to train on the whole data)
block_size = 8

# here we will define the input sequence according to the block size
x = train_data[:block_size]
y = train_data[1:block_size+1]
for t in range(block_size):
  context = x[:t+1]
  target = y[t]
  print(f' When input is {context} the target is: {target}')

torch.manual_seed(1337)
batch_size = 4 # how many independent sequences will we process in parallel?
block_size = 8 # what is the maximum context length for predictions?

def get_batch(split):
    # generate a small batch of data of inputs x and targets y
    data = train_data if split == 'train' else val_data
    ix = torch.randint(len(data) - block_size, (batch_size,))
    x = torch.stack([data[i:i+block_size] for i in ix])
    y = torch.stack([data[i+1:i+block_size+1] for i in ix])
    return x, y

xb, yb = get_batch('train')
print('inputs:')
print(xb.shape)
print(xb)
print('targets:')
print(yb.shape)
print(yb)

print('----')

for b in range(batch_size): # batch dimension
    for t in range(block_size): # time dimension
        context = xb[b, :t+1]
        target = yb[b,t]
        print(f"when input is {context.tolist()} the target: {target}")

print(xb) # our input to the transformer

import torch
import torch.nn as nn
import torch.nn.functional as F

# hyperparameters
batch_size = 32 # number of sequences to be processed paralelly
block_size = 8 # the max context length for the predictions
max_iters = 3000
eval_interval = 300
learning_rate = 0.01
device = 'cuda' if torch.cuda.is_available() else 'cpu'
eval_iters = 200
n_embed = 32

torch.manual_seed(1337)

# Define a simple bigram language model
class BigramLanguageModel(nn.Module):
    def __init__(self, vocab_size):
        super().__init__()
        # Embedding table: each token maps directly to logits for next token
        self.embedding = nn.Embedding(vocab_size, n_embed)

    def forward(self, idx, targets=None):
        # Input: idx shape (B, T), output logits shape (B, T, vocab_size)
        logits = self.embedding(idx)

        loss = None
        if targets is not None:
            # Reshape for cross-entropy: (B*T, vocab_size) vs (B*T,)
            B, T, C = logits.shape
            logits = logits.view(B * T, C)
            targets = targets.view(B * T)
            loss = F.cross_entropy(logits, targets)

        return logits, loss

    def generate(self, idx, max_new_tokens):
        # Autoregressive generation for a given input idx of shape (B, T)
        for _ in range(max_new_tokens):
            logits, _ = self(idx)               # (B, T, vocab_size)
            logits = logits[:, -1, :]           # Get logits for last token: (B, vocab_size)
            probs = F.softmax(logits, dim=-1)   # Convert to probabilities
            next_token = torch.multinomial(probs, num_samples=1)  # Sample next token: (B, 1)
            idx = torch.cat((idx, next_token), dim=1)  # Append to sequence: (B, T+1)
        return idx

m = BigramLanguageModel()
logits, loss = m(xb, yb)
print(logits.shape)
print(loss)
print(decode(m.generate(idx=torch.zeros((1,1), dtype=torch.long), max_new_tokens=100)[0].tolist()))

# creating a PyTorch optimizer
optimizer = torch.optim.AdamW(m.parameters(), lr=1e-3)

batch_size = 32
for steps in range(10000):
  # sample a batch of data
  xb, yb = get_batch('train')

  #evaluate the loss
  logits, loss = m(xb, yb)
  optimizer.zero_grad(set_to_none=True)
  loss.backward()
  optimizer.step()

print(loss.item())

print(decode(m.generate(idx=torch.zeros((1,1), dtype=torch.long), max_new_tokens=400)[0].tolist()))

# creading a module for single head self-attention
class Head(nn.Modeule):
    def __init__(self, head_size):
        super().__init__()
        self.key = nn.Linear(n_embed, head_size, bias=False)
        self.query = nn.Linear(n_embed, head_size, bias=False)
        self.value = nn.Linear(n_embed, head_size, bias=False)
        self.register_buffer('tril', torch.tril(torch.ones(block_size, block_size)))

    def forward(self, x):
        B,T,C = x.shape
        k = self.key(x) # (B,T,C)
        q = self.query(x) # (B,T,C)
        # compute attention score ('affinities')
        wei = q @ k.transpose(-2,-1) * C**-0.5 #(B,T,C) @ (B,T,C) ---> (B,T,T)
        wei = wei.masked_fill(self.tril[:T,:T] == 0, float('-inf')) #(B,T,T)
        wei = F.softmax(wei, dim=-1) #(B,T,T)
        # perform the weighted aggregation of the values
        v = self.value(x) # (B,T,C)
        out = wei @ v # (B,T,T) @ (B,T,C) --> (B,T,C)
        return out