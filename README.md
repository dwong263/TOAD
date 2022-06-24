# TOAD
## Tool for Oximetry Analysis in Dialysis
This software is an in-house tool used by the Lilbeth Caberto Kidney Clinical Research Unit (KCRU) at London Health Sciences Centre (LHSC) for semi-automated analysis of CVInsight data.  This tool has been minimally tested, but should work as described below.

## Basic Usage
### Running the Application
Compiled versions of the software are provided in `compiled/macOS/`.  The author uses an M1 MacBook Pro, so only compiled versions are available for macOS arm64 (M1 and M2 MacBooks) and macOS x86_64 (Intel-based MacBooks) architectures.  If you are using Windows or Linux, please run the software with your local installation of Python.  Double-click on the application corresponding to your machine's architecture to open.

### Loading a CVInsight Dataset
Hit the `Browse` button to find the folder containing the CVInsight files for a single subject.  The software assumes there is **one** `*_data.txt` file and **one** `*_eventlog.txt` within the folder.  An example of a valid CVInsight dataset is shown below:

![CVInsight Dataset](docs/FileStructure.png)

Hit the `Open` button to open the dataset.  If successfully read, there will be an indication showing which files are read in and a plot visualizing the % Change in Pulse Strength will be shown.

### Plotting

### Analysis of Metrics

### Saving the Analysis
