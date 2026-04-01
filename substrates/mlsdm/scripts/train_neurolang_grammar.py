#!/usr/bin/env python3
"""
Offline training script for NeuroLang grammar models.

This script trains the actor and critic models offline and saves
the trained weights to a checkpoint file. This allows production
deployments to use pre-trained weights without training overhead.

Usage:
    python scripts/train_neurolang_grammar.py --epochs 3 --output config/neurolang_grammar.pt
"""

import argparse
import sys
from pathlib import Path

import torch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mlsdm.extensions.neuro_lang_extension import (
    CriticalPeriodTrainer,
    InnateGrammarModule,
    LanguageDataset,
    all_sentences,
    is_secure_mode_enabled,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Train NeuroLang grammar models offline")
    parser.add_argument(
        "--epochs", type=int, default=3, help="Number of training epochs (default: 3)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="config/neurolang_grammar.pt",
        help="Output path for checkpoint file (default: config/neurolang_grammar.pt)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    # Security: Block training when secure mode is enabled
    if is_secure_mode_enabled():
        raise SystemExit("Secure mode enabled: offline training is not permitted.")

    args = parse_args(argv)

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Training NeuroLang grammar models...")
    print(f"Epochs: {args.epochs}")
    print(f"Output: {args.output}")

    # Initialize dataset
    dataset = LanguageDataset(all_sentences)
    vocab_size = len(dataset.vocab)
    print(f"Vocabulary size: {vocab_size}")

    # Initialize models
    actor = InnateGrammarModule(vocab_size)
    critic = InnateGrammarModule(vocab_size)

    # Set device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    actor.to(device)
    critic.to(device)

    # Train models
    trainer = CriticalPeriodTrainer(actor, critic, dataset, epochs=args.epochs)
    print("Starting training...")
    trainer.train()
    print("Training complete!")

    # Save checkpoint
    checkpoint = {
        "actor": actor.state_dict(),
        "critic": critic.state_dict(),
        "vocab_size": vocab_size,
        "epochs": args.epochs,
    }

    torch.save(checkpoint, args.output)
    print(f"Checkpoint saved to: {args.output}")

    # Verify checkpoint can be loaded
    # Note: This loads a checkpoint we just created, so it's safe
    print("Verifying checkpoint...")
    loaded_checkpoint = torch.load(args.output, map_location=device, weights_only=True)  # nosec B614
    assert "actor" in loaded_checkpoint
    assert "critic" in loaded_checkpoint
    print("Checkpoint verified successfully!")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
