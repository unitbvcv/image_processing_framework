from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import pyqtSlot

from Application.Models.PlotterWindowModel import PlotterWindowModel
from Application.Models.PlottingFunctionModel import PlottingFunctionModel
from Application.Views.PlotterWindowView import PlotterWindowView
import Application.PlottingAlgorithms as PlottingAlgorithms


class PlotterWindowVM(QtCore.QObject):
    """
    TODO: document PlotterWindowViewModel
    """

    closingWindow = QtCore.pyqtSignal(QtGui.QCloseEvent, name="closingWindow")
    needOriginalImageData = QtCore.pyqtSignal(str, name='needOriginalImageData')
    needProcessedImageData = QtCore.pyqtSignal(str, name='needProcessedImageData')

    def __init__(self, parent=None):
        """
        TODO: document PlotterWindowViewModel constructor
        :param parent:
        """
        super().__init__(parent)

        # Instantiate the model
        self._model = PlotterWindowModel()
        for functionName in PlottingAlgorithms.registeredAlgorithms.keys():
            self._model.functionModels[functionName] = PlottingFunctionModel()

        # Instantiate the view
        self._view = PlotterWindowView()

        # Connect the view
        self._view.closing.connect(self.closingWindow)
        # can't connect to currentIndexChanged[str]; why? don't ask me...
        self._view.comboBoxFunction.currentIndexChanged[int].connect(self._functionComboBoxIndexChanged)
        self._view.listWidgetVisibleOriginalImage.itemSelectionChanged.connect(
            self._visiblePlotsOriginalImageSelectionChangedEvent)
        self._view.listWidgetVisibleProcessedImage.itemSelectionChanged.connect(
            self._visiblePlotsProcessedImageSelectionChangedEvent)
        self._view.pushButtonScaleAndCenter.pressed.connect(self._scaleAndCenterButtonPressed)

    def showWindow(self):
        """Shows the plotter window.

        Returns:
             None

        """
        self._view.show()

    @property
    def isVisible(self):
        """
        TODO: document PlotterWindowViewModel.isVisible
        :return:
        """
        return self._view.isVisible()

    def updateOriginalImageFunctionData(self, functionName, plotDataItems):
        self._model.functionModels[functionName].originalImagePlotDataItems.availablePlotDataItems = plotDataItems
        self._model.functionModels[functionName].originalImagePlotDataItems.isDirty = False

    def updateProcessedImageFunctionData(self, functionName, plotDataItems):
        self._model.functionModels[functionName].processedImagePlotDataItems.availablePlotDataItems = plotDataItems
        self._model.functionModels[functionName].processedImagePlotDataItems.isDirty = False

    def setOriginalImageDataAsDirty(self, functionName):
        self._model.functionModels[functionName].originalImagePlotDataItems.isDirty = True

    def setProcessedImageDataAsDirty(self, functionName):
        self._model.functionModels[functionName].processedImagePlotDataItems.isDirty = True

    def refresh(self):
        # if the data for the current function is dirty signal needData
        # update the view
        # basically this is what _functionComboBoxIndexChanged does, but calling context is different
        self._functionComboBoxIndexChanged(self._view.comboBoxFunction.currentIndex())

    def reset(self):
        """
        TODO: document PlotterWindowViewModel resetPlotter
        :return:
        """

        self._clearView()

        # Clearing the model
        for plottingFunctionModel in self._model.functionModels.values():
            plottingFunctionModel.originalImagePlotDataItems.clear()
            plottingFunctionModel.processedImagePlotDataItems.clear()

    def _clearView(self):
        # TODO: verifica daca mai e necesar clear pe legend (din documentatia de pyqtgraph, cred ca nu)
        currentFunctionName = self._view.comboBoxFunction.currentText()
        originalImagePlotDataItems = self._model.functionModels[currentFunctionName].originalImagePlotDataItems
        currentFunctionName = self._view.comboBoxFunction.currentText()
        processedImagePlotDataItems = self._model.functionModels[currentFunctionName].processedImagePlotDataItems
        self._view.clearPlotItemsLegends(originalImagePlotDataItems.visiblePlotDataItems.keys(),
                                         processedImagePlotDataItems.visiblePlotDataItems.keys())
        self._view.clearPlotItems()
        self._view.clearListWidgets()

    @pyqtSlot()
    def _scaleAndCenterButtonPressed(self):
        """
        TODO: document PlotterWindowViewModel _scaleAndCenterButtonPressed
        :return:
        """
        plots = list(self._model.visiblePlotDataItemsOriginalImage.values()) + \
            list(self._model.visiblePlotDataItemsProcessedImage.values())

        self._view.scaleAndCenterToPlots(plots)

    @pyqtSlot(int)
    def _functionComboBoxIndexChanged(self, functionIndex):
        functionName = self._view.comboBoxFunction.itemText(functionIndex)
        if self._model.functionModels[functionName].originalImagePlotDataItems.isDirty:
            self.needOriginalImageData.emit(functionName)

        if self._model.functionModels[functionName].processedImagePlotDataItems.isDirty:
            self.needProcessedImageData.emit(functionName)

        # because the 3 windows are on the same thread, THEORETICALLY our connections are direct/synchronous
        # so a slot is called immediately after the signal is emitted and the emitting function is resumed
        # after the slot finished ... theoretically
        # because of that, I can call a refresh on the plotter as the data is all up to date
        self._updateView()

    def _updateView(self):
        # PRECONDITION: data is NOT dirty
        self._clearView()

        currentFunctionName = self._view.comboBoxFunction.currentText()
        currentFunctionModel = self._model.functionModels[currentFunctionName]

        self._view.populateListWidgets(
            currentFunctionModel.originalImagePlotDataItems.availablePlotDataItems.keys(),
            currentFunctionModel.processedImagePlotDataItems.availablePlotDataItems.keys())
        self._view.listWidgetVisibleOriginalImage.selectAll()  # hack; credits to Cosmin
        self._view.listWidgetVisibleProcessedImage.selectAll()

    def _visiblePlotsSelectionChanged(self, plotItem, availablePlotDataItems, visiblePlotDataItems, listWidget):
        """
        TODO: document PlotterWindowViewModel _visiblePlotsSelectionChanged
        :param plotItem:
        :param availablePlotDataItems:
        :param visiblePlotDataItems:
        :param listWidget:
        :return:
        """
        selectedPlotsNames = set([item.text() for item in listWidget.selectedItems()])
        visiblePlotsNames = set(visiblePlotDataItems.keys())

        if selectedPlotsNames > visiblePlotsNames:
            # here one or more plots have been selected
            plotDataItemsNamesToAdd = selectedPlotsNames - visiblePlotsNames

            plotDataItemsToAdd = []

            # adding the plots in model from available to visible
            for plotDataItemName in plotDataItemsNamesToAdd:
                plotDataItem = availablePlotDataItems[plotDataItemName]
                visiblePlotDataItems[plotDataItemName] = plotDataItem
                plotDataItemsToAdd.append(plotDataItem)

            # updating the view
            self._view.addPlotDataItems(plotItem, plotDataItemsToAdd)

        elif visiblePlotsNames > selectedPlotsNames:
            # here one or more plots have been deselected
            plotDataItemsNamesToRemove = visiblePlotsNames - selectedPlotsNames

            plotDataItemsToRemove = [plotDataItem for (plotDataItemName, plotDataItem)
                                     in visiblePlotDataItems.items()
                                     if plotDataItemName in plotDataItemsNamesToRemove]

            # removing them from view
            self._view.removePlotDataItems(plotItem, plotDataItemsToRemove)

            # removing them from the visible plots in the model
            for plotDataItemName in plotDataItemsNamesToRemove:
                del visiblePlotDataItems[plotDataItemName]

    @pyqtSlot()
    def _visiblePlotsOriginalImageSelectionChangedEvent(self):
        """
        TODO document PlotterWindowViewModel _visiblePlotsOriginalImageSelectionChangedEvent
        :return:
        """

        currentFunctionName = self._view.comboBoxFunction.currentText()
        originalImagePlotDataItems = self._model.functionModels[currentFunctionName].originalImagePlotDataItems

        self._visiblePlotsSelectionChanged(
            self._view.plotItemOriginalImage,
            originalImagePlotDataItems.availablePlotDataItems,
            originalImagePlotDataItems.visiblePlotDataItems,
            self._view.listWidgetVisibleOriginalImage)

    @pyqtSlot()
    def _visiblePlotsProcessedImageSelectionChangedEvent(self):
        """
        TODO: document PlotterWindowViewModel _visiblePlotsProcessedImageSelectionChangedEvent
        :return:
        """

        currentFunctionName = self._view.comboBoxFunction.currentText()
        processedImagePlotDataItems = self._model.functionModels[currentFunctionName].processedImagePlotDataItems

        self._visiblePlotsSelectionChanged(
            self._view.plotItemProcessedImage,
            processedImagePlotDataItems.availablePlotDataItems,
            processedImagePlotDataItems.visiblePlotDataItems,
            self._view.listWidgetVisibleProcessedImage)
