"""
testlab/export_helper.py
------------------------
Helper leggero per gli script utente.
Lo script importa save_figure() e la chiama al posto di plt.show().
Se lanciato dalla GUI, salva la figura nel path indicato dalla variabile
d'ambiente TESTLAB_EXPORT_PATH. Se lanciato standalone, si comporta
come plt.show() normale.

Uso nello script Python:
    from testlab.export_helper import save_figure
    fig, ax = plt.subplots()
    ax.plot(...)
    save_figure(fig)          # sostituisce plt.show()

Uso nello script MATLAB (testlab_save_figure.m generato automaticamente):
    testlab_save_figure(gcf)
"""

import os
from pathlib import Path


def save_figure(fig, also_show: bool = False):
    """
    Salva fig nel path definito da TESTLAB_EXPORT_PATH.
    Se la variabile non è impostata, chiama semplicemente fig.show()
    o plt.show() a seconda del tipo di oggetto.
    """
    export_path = os.environ.get("TESTLAB_EXPORT_PATH", "")

    if export_path:
        Path(export_path).parent.mkdir(parents=True, exist_ok=True)
        # supporta matplotlib Figure e plotly Figure
        _type = type(fig).__module__
        if "plotly" in _type:
            import plotly.io as pio
            ext = Path(export_path).suffix.lower()
            fmt = ext.lstrip(".") or "png"
            pio.write_image(fig, export_path, format=fmt)
        else:
            fig.savefig(export_path)
        print(f"[testlab] figura salvata in: {export_path}")
        if also_show:
            _show(fig)
    else:
        _show(fig)


def _show(fig):
    try:
        fig.show()
    except AttributeError:
        import matplotlib.pyplot as plt
        plt.show()
