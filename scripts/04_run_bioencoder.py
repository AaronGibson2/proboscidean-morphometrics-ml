import bioencoder

bioencoder.configure(
    root_dir="../bioencoder_wd",
    run_name="proboscidean_v1",
    create=True
)

bioencoder.split_dataset(
    image_dir="../segmented_teeth",
    root_dir="../bioencoder_wd",
    run_name="proboscidean_v1",
    max_ratio=6,
    random_seed=42,
    val_percent=0.2,
    min_per_class=2
)

bioencoder.train(
    config_path="../bioencoder_configs/train_stage1.yml",
    root_dir="../bioencoder_wd",
    run_name="proboscidean_v1"
)

bioencoder.swa(
    config_path="../bioencoder_configs/swa_stage1.yml",
    root_dir="../bioencoder_wd",
    run_name="proboscidean_v1"
)

bioencoder.interactive_plots(
    config_path="../bioencoder_configs/plot_stage1.yml",
    root_dir="../bioencoder_wd",
    run_name="proboscidean_v1"
)