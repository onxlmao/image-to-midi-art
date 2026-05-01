from setuptools import setup, find_packages

setup(
    name="image-to-midi-art",
    version="1.0.0",
    description="Convert images into MIDI art files — pixel position maps to pitch, brightness to velocity.",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "Pillow>=10.0.0",
        "numpy>=1.24.0",
        "midiutil>=1.2.1",
    ],
    entry_points={
        "console_scripts": [
            "image-to-midi=image_to_midi.cli:main",
        ],
    },
)
