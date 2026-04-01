"""
Production Chatbot Example with MLSDM Cognitive Governance

This example demonstrates a production-ready chatbot implementation using
MLSDM to provide:
- Moral filtering of user inputs and responses
- Context-aware responses with memory
- Graceful handling of sleep phases
- Monitoring and logging
- Error handling

Author: neuron7x
License: MIT
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np

try:
    from mlsdm.core.llm_wrapper import LLMWrapper
except ImportError:
    print("Error: Cannot import LLMWrapper. Make sure you're running from the project root.")
    exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """Represents a chat message."""

    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    moral_score: float
    accepted: bool = True


class ToxicityScorer:
    """Simple toxicity scorer for demonstration.

    In production, replace with a real toxicity classifier like:
    - Perspective API
    - Detoxify
    - Custom trained model
    """

    TOXIC_KEYWORDS = [
        "hate",
        "kill",
        "destroy",
        "attack",
        "violence",
        "racist",
        "sexist",
        "offensive",
        "abuse",
    ]

    @classmethod
    def score(cls, text: str) -> float:
        """Score text for toxicity (0.0 = toxic, 1.0 = safe).

        Args:
            text: Input text to score

        Returns:
            Moral score between 0.0 and 1.0
        """
        text_lower = text.lower()

        # Check for toxic keywords
        toxic_count = sum(1 for keyword in cls.TOXIC_KEYWORDS if keyword in text_lower)

        score = 0.9
        if toxic_count > 0:
            score = max(0.1, 1.0 - toxic_count * 0.3)

        # Length-based adjustment (very short or very long can be suspicious)
        word_count = len(text_lower.split())
        if word_count < 3:
            score = min(score, 0.7)
        elif word_count > 200:
            score = min(score, 0.8)

        return score


class MockLLM:
    """Mock LLM for demonstration purposes.

    In production, replace with real LLM integration:
    - OpenAI GPT-3.5/4
    - Anthropic Claude
    - Local models via transformers
    """

    RESPONSES = {
        "hello": "Hello! How can I help you today?",
        "how are you": "I'm functioning well, thank you for asking! How can I assist you?",
        "quantum": "Quantum computing uses quantum mechanics principles like superposition and entanglement to perform computations that would be infeasible for classical computers.",
        "weather": "I don't have access to real-time weather data, but I can discuss weather concepts or help you find weather information.",
        "help": "I'm here to assist you! You can ask me questions, have conversations, or request information on various topics.",
        "default": "That's an interesting question. Let me think about that...",
    }

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        """Generate response based on prompt.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response text
        """
        # Simple keyword matching for demo
        prompt_lower = prompt.lower()

        for keyword, response in self.RESPONSES.items():
            if keyword in prompt_lower:
                return response

        return self.RESPONSES["default"] + f" (prompt length: {len(prompt)} chars)"


class SimpleEmbedder:
    """Simple embedding function for demonstration.

    In production, use proper embeddings:
    - sentence-transformers (all-MiniLM-L6-v2)
    - OpenAI embeddings
    - Custom trained embeddings
    """

    def __init__(self, dim: int = 384):
        """Initialize embedder.

        Args:
            dim: Embedding dimension
        """
        self.dim = dim
        np.random.seed(42)  # For reproducibility in demo

    def encode(self, text: str) -> np.ndarray:
        """Encode text to vector.

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        # Create deterministic "embeddings" based on text hash
        # In production, use real embeddings!
        text_hash = hash(text.lower())
        np.random.seed(text_hash % (2**32))
        embedding = np.random.randn(self.dim).astype(np.float32)

        # Normalize
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)

        return embedding


class ProductionChatbot:
    """Production chatbot with MLSDM cognitive governance."""

    def __init__(self, llm: Any | None = None, embedder: Any | None = None, dim: int = 384):
        """Initialize chatbot.

        Args:
            llm: LLM instance (defaults to MockLLM)
            embedder: Embedder instance (defaults to SimpleEmbedder)
            dim: Embedding dimension
        """
        self.llm = llm or MockLLM()
        self.embedder = embedder or SimpleEmbedder(dim)
        self.toxicity_scorer = ToxicityScorer()

        # Initialize MLSDM wrapper
        logger.info("Initializing MLSDM cognitive wrapper...")
        self.wrapper = LLMWrapper(
            llm_generate_fn=self.llm.generate,
            embedding_fn=self.embedder.encode,
            dim=dim,
            capacity=20000,
            wake_duration=8,
            sleep_duration=3,
            initial_moral_threshold=0.50,
        )

        # Chat history
        self.history: list[ChatMessage] = []

        # Statistics
        self.stats = {"total_messages": 0, "accepted": 0, "rejected": 0, "sleep_phase_waits": 0}

        logger.info("Chatbot initialized successfully")

    def process_message(self, user_input: str, max_retries: int = 3) -> ChatMessage:
        """Process user message and generate response.

        Args:
            user_input: User's input text
            max_retries: Maximum retries if in sleep phase

        Returns:
            ChatMessage with response
        """
        # Score toxicity
        moral_score = self.toxicity_scorer.score(user_input)
        logger.info(f"User input moral score: {moral_score:.2f}")

        # Try to generate response
        for attempt in range(max_retries):
            try:
                result = self.wrapper.generate(
                    prompt=user_input, moral_value=moral_score, context_top_k=5
                )

                # Update statistics
                self.stats["total_messages"] += 1

                if result["accepted"]:
                    self.stats["accepted"] += 1

                    # Create response message
                    response_msg = ChatMessage(
                        role="assistant",
                        content=result["response"],
                        timestamp=datetime.now(),
                        moral_score=moral_score,
                        accepted=True,
                    )

                    # Add to history
                    self.history.append(
                        ChatMessage(
                            role="user",
                            content=user_input,
                            timestamp=datetime.now(),
                            moral_score=moral_score,
                            accepted=True,
                        )
                    )
                    self.history.append(response_msg)

                    logger.info(
                        f"Response generated successfully "
                        f"(phase: {result['phase']}, "
                        f"step: {result['step']}, "
                        f"context: {result['context_items']} items)"
                    )

                    return response_msg

                else:
                    self.stats["rejected"] += 1
                    note = result["note"]

                    if "sleep phase" in note.lower():
                        # Sleep phase - wait and retry
                        self.stats["sleep_phase_waits"] += 1
                        logger.warning(
                            f"In sleep phase (attempt {attempt + 1}/{max_retries}). "
                            "Waiting 1 second..."
                        )
                        time.sleep(1)
                        continue

                    elif "morally rejected" in note.lower():
                        # Moral rejection - inform user
                        logger.warning(f"Message rejected due to content policy: {note}")
                        return ChatMessage(
                            role="assistant",
                            content="I cannot process this request due to content policy. Please rephrase your message.",
                            timestamp=datetime.now(),
                            moral_score=moral_score,
                            accepted=False,
                        )

                    else:
                        # Unknown rejection
                        logger.error(f"Message rejected: {note}")
                        return ChatMessage(
                            role="assistant",
                            content="I cannot process this request at the moment. Please try again.",
                            timestamp=datetime.now(),
                            moral_score=moral_score,
                            accepted=False,
                        )

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                return ChatMessage(
                    role="assistant",
                    content="An error occurred processing your request. Please try again.",
                    timestamp=datetime.now(),
                    moral_score=moral_score,
                    accepted=False,
                )

        # Max retries exceeded
        logger.error(f"Max retries ({max_retries}) exceeded")
        return ChatMessage(
            role="assistant",
            content="The system is currently consolidating memory. Please try again in a moment.",
            timestamp=datetime.now(),
            moral_score=moral_score,
            accepted=False,
        )

    def get_system_state(self) -> dict[str, Any]:
        """Get current system state.

        Returns:
            Dictionary with system state
        """
        state = self.wrapper.get_state()
        state["chatbot_stats"] = self.stats
        state["message_count"] = len(self.history)
        return state

    def print_statistics(self) -> None:
        """Print chatbot statistics."""
        state = self.get_system_state()

        print("\n" + "=" * 60)
        print("CHATBOT STATISTICS")
        print("=" * 60)

        print("\nMessages:")
        print(f"  Total: {self.stats['total_messages']}")
        print(f"  Accepted: {self.stats['accepted']}")
        print(f"  Rejected: {self.stats['rejected']}")
        print(f"  Sleep waits: {self.stats['sleep_phase_waits']}")

        print("\nCognitive State:")
        print(f"  Phase: {state['phase']}")
        print(f"  Step: {state['step']}")
        print(f"  Moral threshold: {state['moral_threshold']:.2f}")
        print(f"  Moral EMA: {state['moral_ema']:.2f}")

        print("\nMemory:")
        qilm = state["qilm_stats"]
        print(f"  Used: {qilm['used']:,}/{qilm['capacity']:,} vectors")
        print(f"  Usage: {(qilm['used']/qilm['capacity']*100):.1f}%")
        print(f"  Size: {qilm['memory_mb']:.2f} MB")

        print("\nSynaptic Memory:")
        synaptic = state["synaptic_norms"]
        print(f"  L1 (fast): {synaptic['L1']:.4f}")
        print(f"  L2 (medium): {synaptic['L2']:.4f}")
        print(f"  L3 (slow): {synaptic['L3']:.4f}")

        print("=" * 60 + "\n")


def demo_conversation():
    """Run demonstration conversation."""
    print("\n" + "=" * 60)
    print("MLSDM PRODUCTION CHATBOT DEMO")
    print("=" * 60)
    print("\nInitializing chatbot with cognitive governance...")

    # Create chatbot
    chatbot = ProductionChatbot()

    # Demonstration conversation
    conversation = [
        "Hello! How are you?",
        "Tell me about quantum computing",
        "What's the weather like?",
        "Can you help me?",
        # Test with potentially toxic input (will be scored low)
        "I hate this conversation",  # Should be filtered
        "Tell me a joke",
        "What is artificial intelligence?",
    ]

    print(f"\nStarting conversation ({len(conversation)} messages)...\n")

    for i, user_input in enumerate(conversation, 1):
        print(f"\n{'─'*60}")
        print(f"Message {i}/{len(conversation)}")
        print(f"{'─'*60}")
        print(f"👤 User: {user_input}")

        # Process message
        response = chatbot.process_message(user_input)

        if response.accepted:
            print(f"🤖 Bot: {response.content}")
        else:
            print(f"⚠️  Bot: {response.content}")
            print(f"   (Rejection reason: moral_score={response.moral_score:.2f})")

        # Small delay between messages
        time.sleep(0.5)

    # Print final statistics
    chatbot.print_statistics()

    print("\nDemo completed successfully!")


def interactive_mode():
    """Run interactive chatbot mode."""
    print("\n" + "=" * 60)
    print("MLSDM INTERACTIVE CHATBOT")
    print("=" * 60)
    print("\nInitializing chatbot...")

    # Create chatbot
    chatbot = ProductionChatbot()

    print("\nChatbot ready! Type 'quit' to exit, 'stats' for statistics.\n")

    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("\nGoodbye!")
                chatbot.print_statistics()
                break

            if user_input.lower() == "stats":
                chatbot.print_statistics()
                continue

            # Process message
            response = chatbot.process_message(user_input)

            if response.accepted:
                print(f"Bot: {response.content}\n")
            else:
                print(f"Bot (rejected): {response.content}\n")

        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            chatbot.print_statistics()
            break
        except Exception as e:
            print(f"Error: {e}")
            logger.error(f"Unexpected error: {e}", exc_info=True)


if __name__ == "__main__":
    import sys

    print("\nMLSDM Production Chatbot Example")
    print("=" * 60)

    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        # Interactive mode
        interactive_mode()
    else:
        # Demo mode
        demo_conversation()

        print("\nTo try interactive mode, run:")
        print("  python examples/production_chatbot_example.py --interactive")
