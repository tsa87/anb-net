import json
import argparse

import numpy as np
import torch

from dig.ggraph.dataset import ZINC250k
from molecule_optimizer.externals.fast_jtnn.datautils import SemiMolTreeFolder
from molecule_optimizer.runner.semi_jtvae import SemiJTVAEGeneratorPredictor
from torch_geometric.data import DenseDataLoader

np.random.seed(42)
torch.manual_seed(42)


def _setup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config_path", type=str, default=None)
    parser.add_argument("--help", "-h", action="help")
    return parser


def main():
    """
    Run an experiment.
    Sample command:
    ```
    python training/run_experiment.py --config_path=configs/rand_gen_zinc250k_config_dict.json
    ```
    """
    parser = _setup_parser()
    args = parser.parse_args()
    conf = json.load(open(args.config_path))

    print("Processing Dataset...")
    _ = ZINC250k(
        one_shot=False,
        use_aug=False,
        processed_filename=conf["data"]["processed_path"],
    )
    zinc_250_jt = torch.load(conf["data"]["processed_path"])
    smiles = zinc_250_jt[-1]
    labels = zinc_250_jt[0].y

    jtvae = SemiJTVAEGeneratorPredictor(smiles)
    jtvae.get_model(
        "rand_gen",
        config={
            "hidden_size": conf["hidden_size"],
            "latent_size": conf["latent_size"],
            "depthT": conf["depthT"],
            "depthG": conf["depthG"],
            "label_size": 1,
            "label_mean": np.mean(labels),
            "label_var": np.var(labels),
        },
    )

    preprocessed, labels = jtvae.preprocess(smiles, labels)

    loader = SemiMolTreeFolder(
        preprocessed,
        labels,
        jtvae.vocab,
        conf["batch_size"],
        num_workers=conf["num_workers"],
    )

    print("Training model...")
    jtvae.train_rand_gen(
        loader=loader,
        lr=conf["lr"],
        wd=conf["weight_decay"],
        max_epochs=conf["max_epochs"],
        model_conf_dict=conf["model"],
        save_interval=conf["save_interval"],
        save_dir=conf["save_dir"],
    )
