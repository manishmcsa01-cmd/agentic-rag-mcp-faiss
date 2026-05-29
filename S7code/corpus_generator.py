import os
from pathlib import Path

# AI/ML topics and their high-fidelity contents
corpus_data = {
    "active_learning": """# Active Learning

Active learning is a semi-supervised machine learning framework in which the algorithm dynamically queries a user or oracle to label new data points. The goal is to maximize model performance while minimizing labeling costs.

It is particularly useful when unlabeled data is abundant but labeling is expensive, time-consuming, or requires domain expertise. Standard querying strategies include uncertainty sampling, query-by-committee, and expected model change.
""",
    "attention_mechanism": """# Attention Mechanism

The attention mechanism is a technique that mimics cognitive attention, allowing models to focus on specific parts of the input sequence when generating an output. First introduced for machine translation in recurrent neural networks, it enables the alignment of source and target sentences.

Instead of compressing the entire input into a single fixed-length context vector, the model computes dynamic weights over all input hidden states, allowing it to preserve long-range dependencies.
""",
    "batch_normalization": """# Batch Normalization

Batch Normalization is a technique to improve the speed, performance, and stability of artificial neural networks. It normalizes the inputs of each layer for each mini-batch, which stabilizes the learning process.

By mitigating the internal covariate shift, batch normalization allows the use of much higher learning rates and makes the network less sensitive to initialization, acting as a mild form of regularization.
""",
    "bert": """# BERT (Bidirectional Encoder Representations from Transformers)

BERT is a pre-trained natural language processing model developed by Google. Unlike traditional sequential models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers.

It uses a Masked Language Model (MLM) and Next Sentence Prediction (NSP) task during pre-training and can be fine-tuned with just one additional output layer for a wide range of tasks.
""",
    "chain_of_thought": """# Chain-of-Thought Reasoning

Chain-of-Thought (CoT) reasoning is a prompting technique that encourages large language models to generate intermediate reasoning steps before producing a final answer.

By breaking down a complex problem into sequential logical steps, CoT significantly improves model performance on multi-step reasoning, mathematical problem-solving, and symbolic logic tasks. It allows the model to allocate more computational steps (tokens) to hard problems.
""",
    "contrastive_learning": """# Contrastive Learning

Contrastive learning is a self-supervised learning technique where the model learns representations by contrasting positive pairs against negative pairs. The core idea is to pull representations of similar images close together while pushing representations of different images far apart in the embedding space.

Popular frameworks include SimCLR, MoCo, and CLIP. It has demonstrated state-of-the-art results in unsupervised visual representation learning.
""",
    "dpo": """# Direct Preference Optimization (DPO)

Direct Preference Optimization (DPO) is a stable, simple, and computationally lightweight algorithm for steering large language models to align with human preferences. Unlike traditional RLHF, which fits a separate reward model and runs reinforcement learning (like PPO), DPO directly optimizes the policy network.

It uses a mathematical change of variables to optimize the policy under a binary cross-entropy loss on preference data, completely bypassing the need for a separate reward model or complex reinforcement learning loops.
""",
    "dropout": """# Dropout Regularization

Dropout is a highly effective regularization technique for reducing overfitting in deep neural networks. During training, individual nodes are randomly dropped out of the network (along with their connections) with a probability p.

This prevents units from co-adapting too much, forcing the network to learn redundant representations and robust features that generalize better to unseen data. At test time, all nodes are active, but weights are scaled down.
""",
    "early_stopping": """# Early Stopping

Early stopping is a regularization technique used to prevent overfitting when training machine learning models via iterative methods like gradient descent.

By monitoring the model's performance on a separate validation set, training is halted as soon as the validation error begins to rise, even if the training error continues to decrease. This ensures the model retains its generalization capability.
""",
    "embeddings": """# Vector Embeddings

Vector embeddings are low-dimensional, continuous representations of high-dimensional data, such as words, sentences, images, or graphs. They compress complex semantic relationships into a dense vector space where geometric distance (e.g. cosine distance) corresponds to semantic similarity.

Modern embedding pipelines use deep networks to place conceptually related items close to one another, forming the basis for semantic search and retrieval systems.
""",
    "f1_score": """# F1 Score

The F1 score is a metric that measures a model's accuracy on a dataset by computing the harmonic mean of precision and recall.

Unlike arithmetic mean, the harmonic mean penalizes extreme values. An F1 score is particularly valuable when evaluating models on imbalanced datasets, where standard accuracy can be misleading due to class distribution skew.
""",
    "faiss": """# FAISS (Facebook AI Similarity Search)

FAISS is an open-source library developed by Meta's AI research group for efficient similarity search and clustering of dense vectors. It is highly optimized for searching billions of vectors in high-dimensional spaces, supporting both CPU and GPU execution.

FAISS implements several indexing strategies, such as IndexFlatIP for exact inner product (equivalent to cosine similarity on normalized vectors) and IndexIVFFlat for inverted file indexing.
""",
    "few_shot_learning": """# Few-Shot Learning

Few-Shot Learning is a machine learning setup where a model is trained or prompted to generalize to new tasks given only a very small number of training examples or demonstrations.

In large language models, few-shot learning is achieved through in-context learning, where the prompt contains a few examples of input-output pairs before the final target query.
""",
    "fine_tuning": """# Fine-Tuning

Fine-Tuning is the process of taking a pre-trained model (trained on a large, general corpus) and further training it on a smaller, domain-specific dataset to adapt it to a target task.

Fine-tuning adjusts the weights of the existing neural network, enabling it to learn specialized vocabulary, style, formats, or domain knowledge while retaining the general capabilities acquired during pre-training.
""",
    "gans": """# Generative Adversarial Networks (GANs)

GANs are a class of machine learning frameworks designed by Ian Goodfellow and his colleagues. They consist of two neural networks, a Generator and a Discriminator, contesting with each other in a zero-sum game.

The Generator tries to produce realistic synthetic data, while the Discriminator tries to distinguish real data from synthetic data. This adversarial process forces both networks to improve dynamically.
""",
    "gpt_4": """# GPT-4 (Generative Pre-trained Transformer 4)

GPT-4 is a multimodal large language model developed by OpenAI, capable of processing both image and text inputs and generating text outputs.

Built on the Transformer architecture, it exhibits human-level performance on various professional and academic benchmarks. GPT-4 was trained on massive datasets using reinforcement learning from human feedback (RLHF) to align safety and utility.
""",
    "gradient_descent": """# Gradient Descent

Gradient descent is a first-order iterative optimization algorithm for finding the local minimum of a differentiable function. In machine learning, it is used to minimize the loss function by iteratively updating model weights.

Updates are performed in the opposite direction of the gradient of the function at the current point, scaled by a step size known as the learning rate. Common variants include Stochastic Gradient Descent (SGD) and Adam.
""",
    "hyperparameters": """# Hyperparameters

Hyperparameters are the configuration parameters of a machine learning model that are set prior to the training process, rather than learned during training.

Examples include the learning rate, batch size, number of hidden layers, activation functions, and regularization constants. Choosing optimal hyperparameters is often done through grid search, random search, or Bayesian optimization.
""",
    "imagenet": """# ImageNet Dataset

ImageNet is a large visual database designed for use in visual object recognition software research. It contains more than 14 million annotated images across more than 20,000 categories.

The annual ImageNet Large Scale Visual Recognition Challenge (ILSVRC) was a catalyst in the deep learning revolution, leading to breakthroughs like AlexNet in 2012, ResNet in 2015, and Vision Transformers.
""",
    "k_means": """# K-Means Clustering

K-Means is a popular unsupervised machine learning clustering algorithm that groups unlabeled data into K distinct clusters.

It works iteratively by assigning each data point to its nearest cluster centroid (based on Euclidean distance) and then re-computing the centroids of each cluster as the mean of all points assigned to it, repeating until convergence.
""",
    "lora": """# LoRA (Low-Rank Adaptation)

LoRA is a parameter-efficient fine-tuning (PEFT) technique for adapting large language models to downstream tasks. Instead of updating all parameters of the network, LoRA freezes the pre-trained model weights and injects trainable rank decomposition matrices into each layer.

This drastically reduces the number of trainable parameters (often by 99% or more) and lowers memory requirements during training, without introducing inference latency.
""",
    "lstm": """# LSTM (Long Short-Term Memory)

Long Short-Term Memory is a specialized recurrent neural network (RNN) architecture designed to model temporal sequences and long-range dependencies more accurately than standard RNNs.

LSTMs introduce a cell state and three control gates: an input gate, a forget gate, and an output gate. These gates dynamically regulate the flow of information, effectively mitigating the vanishing gradient problem.
""",
    "markov_decision_process": """# Markov Decision Process (MDP)

A Markov Decision Process provides a mathematical framework for modeling decision-making in situations where outcomes are partly random and partly under the control of a decision maker.

An MDP is defined by five elements: a set of states, a set of actions, transition probabilities, a reward function, and a discount factor. It is the fundamental foundational model for reinforcement learning systems.
""",
    "mlp": """# Multi-Layer Perceptron (MLP)

A Multi-Layer Perceptron is a class of feedforward artificial neural network. An MLP consists of at least three layers of nodes: an input layer, a hidden layer, and an output layer.

Except for the input nodes, each node is a neuron that uses a non-linear activation function. MLPs utilize a supervised learning technique called backpropagation for training.
""",
    "model_quantization": """# Model Quantization

Model quantization is a compression technique that converts a model's weights and activations from high-precision representations (like 32-bit floating point FP32) to lower-precision representations (like 8-bit integers INT8).

Quantization reduces memory footprint, lowers storage requirements, and accelerates inference on hardware like edge devices, with minimal loss in model accuracy.
""",
    "multi_agent_systems": """# Multi-Agent Systems

Multi-Agent Systems consist of multiple autonomous, interacting agents cooperating or competing to achieve specific objectives.

In large language models, multi-agent frameworks assign specialized roles, personas, and tools to distinct agents, allowing them to collaborate through structured communication protocols to solve complex software engineering or planning tasks.
""",
    "neural_architecture_search": """# Neural Architecture Search (NAS)

Neural Architecture Search is a subfield of automated machine learning (AutoML) focused on automating the design of artificial neural networks.

NAS algorithms search through a predefined space of network connections, layer types, and hyperparameters to discover architectures that maximize accuracy while minimizing computational cost, often utilizing reinforcement learning or evolutionary algorithms.
""",
    "overfitting": """# Overfitting in Machine Learning

Overfitting occurs when a machine learning model learns the detail and noise in the training data to an extent that it negatively impacts the model's performance on new, unseen validation data.

It happens when the model is too complex relative to the simplicity of the data. Overfitting is mitigated by techniques like dropout, weight decay, early stopping, and data augmentation.
""",
    "ppo": """# Proximal Policy Optimization (PPO)

Proximal Policy Optimization is a family of reinforcement learning algorithms developed by OpenAI. PPO is an on-policy actor-critic algorithm that strikes a balance between ease of implementation, sample complexity, and ease of tuning.

PPO uses a clipped surrogate objective function to constrain the size of policy updates at each step, preventing destabilizing updates and ensuring steady policy improvement during training.
""",
    "precision_and_recall": """# Precision and Recall

Precision and Recall are evaluation metrics used to measure a model's performance on classification tasks, particularly on imbalanced datasets.

Precision is the ratio of true positive predictions to the total predicted positives (measuring quality of positive predictions). Recall is the ratio of true positives to total actual positives (measuring ability to find all positive cases).
""",
    "q_learning": """# Q-Learning

Q-Learning is a model-free reinforcement learning algorithm used to learn the value of an action in a particular state.

It does not require a model of the environment and can handle problems with stochastic transitions and rewards. Q-learning iteratively updates a Q-table or neural network (Deep Q-Network) using the Bellman equation, aiming to find an optimal policy that maximizes cumulative reward.
""",
    "rag": """# Retrieval-Augmented Generation (RAG)

Retrieval-Augmented Generation is an architectural pattern that enhances large language models by integrating a dynamic retrieval mechanism.

Instead of relying solely on the static knowledge frozen in its weights, a RAG system queries an external database (such as a FAISS vector index) using the query's embedding, retrieves relevant document chunks, and injects them into the model's context window to produce accurate, factual responses.
""",
    "random_forest": """# Random Forest

Random Forest is an ensemble learning method for classification, regression, and other tasks that operates by constructing a multitude of decision trees at training time.

For classification tasks, the output is the class selected by the majority of the trees. Random forests introduce bagging (bootstrap aggregating) and feature randomness to prevent overfitting, making them highly robust.
""",
    "react": """# ReAct (Reasoning and Acting)

ReAct is an agent framework that prompt-steers large language models to generate both reasoning traces and task-specific actions in an interleaved manner.

Generating reasoning traces allows the model to induce, track, and update action plans, while actions allow it to interface with external tools (like search engines or APIs) to retrieve factual information and execute concrete tasks.
""",
    "reinforcement_learning": """# Reinforcement Learning (RL)

Reinforcement Learning is an area of machine learning concerned with how intelligent agents ought to take actions in an environment to maximize the cumulative reward.

RL is framed as a Markov Decision Process, where the agent interacts with the environment in discrete steps, observing states, receiving rewards, and updating its policy to make better future decisions based on trials and errors.
""",
    "resnet": """# ResNet (Residual Networks)

ResNet is a deep convolutional neural network architecture introduced by Kaiming He and colleagues. ResNet introduced residual learning and "shortcut connections" that bypass one or more layers.

This architectural innovation solved the vanishing gradient problem in extremely deep networks, allowing networks with hundreds or thousands of layers (like ResNet-152) to be successfully trained.
""",
    "rlhf": """# Reinforcement Learning from Human Feedback (RLHF)

RLHF is a method for aligning large language models with human preferences. The process involves pre-training a language model, gathering human preference data on model completions, training a reward model to score completions based on preferences, and fine-tuning the language model using PPO to maximize the reward.

This technique is fundamental to the alignment and behavior of modern conversational AI assistants.
""",
    "rnn": """# Recurrent Neural Networks (RNN)

Recurrent Neural Networks are a class of artificial neural networks where connections between nodes form a directed graph along a temporal sequence.

This allows RNNs to exhibit temporal dynamic behavior and process variable-length sequences of inputs. However, standard RNNs struggle with long-range dependencies due to the vanishing or exploding gradient problems.
""",
    "rouge": """# ROUGE Evaluation Metric

ROUGE (Recall-Oriented Understudy for Gisting Evaluation) is a set of metrics used for evaluating automatic summarization and machine translation software.

It compares an automatically produced summary or translation against a set of reference (human-produced) summaries, measuring n-gram overlap (like ROUGE-1, ROUGE-2) and longest common subsequence overlap (ROUGE-L).
""",
    "self_attention": """# Self-Attention Mechanism

Self-attention, also known as intra-attention, is an attention mechanism relating different positions of a single sequence in order to compute a representation of the sequence.

In Transformers, self-attention computes Query, Key, and Value vectors for each token, using them to determine how much focus each token should place on every other token in the sequence, enabling massive parallelization.
""",
    "sentence_transformers": """# Sentence Transformers

Sentence Transformers is a Python framework for state-of-the-art sentence, text, and image embeddings. Based on PyTorch and Hugging Face Transformers, it fine-tunes models (such as BERT or RoBERTa) in a siamese network structure to produce high-quality embeddings.

These dense vector representations are optimized to group semantically similar sentences close together, supporting tasks like semantic search, clustered retrieval, and paraphrase mining.
""",
    "softmax": """# Softmax Function

The softmax function is a mathematical function that takes a vector of K real numbers and normalizes it into a probability distribution consisting of K probabilities proportional to the exponentials of the input numbers.

It is widely used as the final activation layer in neural network classifiers to convert raw logits into normalized class probabilities that sum to 1.0.
""",
    "supervised_learning": """# Supervised Learning

Supervised learning is the machine learning task of learning a function that maps an input to an output based on example input-output pairs.

It infers a function from labeled training data consisting of a set of training examples. The model iteratively adjusts its weights to minimize the difference between its predictions and the actual target labels under a loss function.
""",
    "support_vector_machines": """# Support Vector Machines (SVM)

Support Vector Machines are supervised learning models with associated learning algorithms that analyze data for classification and regression analysis.

An SVM constructs a hyperplane or set of hyperplanes in a high-dimensional space, aiming to find the maximum-margin hyperplane that separates different classes with the largest geometric distance to any training data point.
""",
    "t5": """# T5 (Text-to-Text Transfer Transformer)

T5 is a transformer-based model developed by Google that reframes all NLP tasks into a unified text-to-text format.

Whether the task is translation, classification, summarization, or question answering, T5 takes text as input and produces text as output. This unified architecture enables the sharing of pre-trained knowledge across extremely diverse language tasks.
""",
    "tokenization": """# Tokenization in NLP

Tokenization is the process of converting a sequence of characters (text) into a sequence of smaller sub-units called tokens. Tokens can be words, characters, or subwords.

Modern language models use subword tokenization algorithms like Byte-Pair Encoding (BPE) or WordPiece, which balances vocabulary size and out-of-vocabulary words by splitting rare words into frequent subword components.
""",
    "transformer": """# Transformer Architecture

The Transformer is a deep learning architecture introduced in 2017 in the paper "Attention Is All You Need". It has become the foundational design for almost all state-of-the-art language models.

Unlike recurrent architectures, the Transformer relies entirely on self-attention mechanisms to model relationships between input and output tokens, enabling massive parallelization during training and superior long-range dependency tracking.
""",
    "underfitting": """# Underfitting in Machine Learning

Underfitting occurs when a machine learning model is too simple to capture the underlying structure of the training data.

It happens when the model has high bias, leading to poor performance on both the training set and validation set. Underfitting is corrected by increasing model complexity, training for longer epochs, or adding more rich features to the input data.
""",
    "vanishing_gradient": """# Vanishing Gradient Problem

The vanishing gradient problem is a difficulty found in training artificial neural networks with gradient-based learning methods and backpropagation.

In deep networks, gradients can shrink exponentially as they propagate backward through layers, preventing the weights of early layers from changing their value, halting the learning process. It is addressed by residual connections, batch normalization, and ReLU activation.
""",
    "vector_db": """# Vector Databases

A Vector Database is a specialized database designed to store, manage, and query high-dimensional vector embeddings efficiently.

Unlike traditional relational databases, vector databases use specialized index types (such as HNSW, IVF-PQ) to execute Approximate Nearest Neighbor (ANN) search queries, returning the most semantically similar items to a query vector in milliseconds.
""",
    "word2vec": """# Word2Vec

Word2Vec is a pioneering technique for natural language processing published by Tomas Mikolov and colleagues at Google in 2013.

Word2Vec uses shallow two-layer neural networks to learn dense vector representations of words from large corpuses. It implements two main architectures: Continuous Bag-of-Words (CBOW) and Skip-Gram, capturing semantic relationships like "king - man + woman = queen".
""",
    "zero_shot_learning": """# Zero-Shot Learning

Zero-Shot Learning is a machine learning setup where a model is evaluated on a task or category that it did not explicitly see during training.

In large language models, zero-shot learning is demonstrated when a model is prompted to perform a task directly (e.g. translate a sentence, summarize a paragraph) without any prior input-output examples in its prompt context.
"""
}

def generate_corpus():
    # Make sure sandbox exists
    sandbox_dir = Path("sandbox")
    sandbox_dir.mkdir(exist_ok=True)
    
    corpus_dir = sandbox_dir / "corpus"
    corpus_dir.mkdir(exist_ok=True)
    
    print(f"Generating RAG corpus under: {corpus_dir.resolve()}")
    
    for filename, content in corpus_data.items():
        filepath = corpus_dir / f"{filename}.md"
        filepath.write_text(content.strip() + "\n", encoding="utf-8")
        
    print(f"Successfully generated {len(corpus_data)} markdown files in corpus.")

if __name__ == "__main__":
    generate_corpus()
