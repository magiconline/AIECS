import sys
import math
import os
import json
from typing import Any, Optional
import PySide6
from PySide6.QtWidgets import (QApplication, QGraphicsItem, QGraphicsLineItem, QGraphicsTextItem, QMainWindow, QMessageBox, QToolBox, QHBoxLayout, QGraphicsView,
                               QGraphicsScene, QWidget, QToolButton, QComboBox, QFormLayout, QLabel, QButtonGroup,
                               QVBoxLayout, )
from PySide6.QtGui import (QPen, QPolygonF, QAction, QIcon,)
from PySide6.QtCore import (QRectF, Qt, QLineF)



class Arrow(QGraphicsLineItem):
    def __init__(self, start_item, end_item, parent=None, scene=None) -> None:
        super().__init__(parent, scene)
        self.start_item = start_item
        self.end_item = end_item

    def boundingRect(self) -> PySide6.QtCore.QRectF:
        # 由于箭头比直线大，重新计算graphics scene 需要刷新的范围
        return super().boundingRect()

    def shape(self) -> PySide6.QtGui.QPainterPath:
        # 用于检查鼠标碰撞和选择
        return super().shape()

    def update_position(self):
        # 当start_item 与 end_item 移动时更新箭头
        pass 

    def paint(self, painter: PySide6.QtGui.QPainter, option: PySide6.QtWidgets.QStyleOptionGraphicsItem, widget: Optional[PySide6.QtWidgets.QWidget] = ...) -> None:
        # 绘制直线和箭头
        return super().paint(painter, option, widget=widget)



class DiagramItem(QGraphicsTextItem):
    def __init__(self, text, kwargs, pos, parent) -> None:
        super(DiagramItem, self).__init__()

        self.setPos(pos)
        self.setParent(parent)
        self.setFlag(QGraphicsItem.ItemIsMovable)  # 可以移动
        self.setFlag(QGraphicsItem.ItemIsSelectable)  # 可以选中

        self.setPlainText(text)
        self.kwargs = kwargs
        # self.parent_ = parent
        self.in_arrows = []
        self.out_arrows = []

    def show_property(self):
        property_box: QWidget = self.parent().parent().property_box
        property_layout = property_box.layout()
        
        # 清空布局
        while property_layout.rowCount() > 0:
            property_layout.removeRow(0)

        # 添加
        # TODO: 添加k,v property
        for k in self.kwargs:
            pass


    def hide_property(self):
        pass

    def itemChange(self, change: PySide6.QtWidgets.QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        # item 被移动
        if change == QGraphicsItem.ItemPositionChange:
            for arrow in self.in_arrows:
                arrow.updatePosition()
            for arrow in self.out_arrows:
                arrow.updatePosition()
        
        elif change == QGraphicsItem.ItemSelectedChange:
            if self.isSelected():
                # 未选中 -> 选中，显示property
                self.show_property()
            else:
                # 选中 -> 未选中，隐藏property
                self.hide_property()

        return super().itemChange(change, value)

    def focusOutEvent(self, event: PySide6.QtGui.QFocusEvent) -> None:
        # 失去焦点时不可修改text
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        return super().focusOutEvent(event)

    def mouseDoubleClickEvent(self, event: PySide6.QtWidgets.QGraphicsSceneMouseEvent) -> None:
        # 双击可以修改text
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        super().mouseDoubleClickEvent(event)    

    def remove_arrow(self, arrow):
        pass 

    def remove_arrows(self):
        pass 

class DiagramScene(QGraphicsScene):
    # TODO：设置item的Z轴1000，line的Z轴-1000

    def __init__(self, parent):
        super().__init__()
        self.item_mode = None # 'str' , None
        self.item_kwargs = None
        self.pointer_mode = None  # 'pointer', 'line'
        self.line = None
        self.setParent(parent)
        self.in_arrows = []
        self.out_arrows = []
        self.propertys = {}

    def mousePressEvent(self, event: PySide6.QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if event.button() != Qt.LeftButton:  # 只响应左键
            return

        # 摁下左键：添加item 或 添加line 或 无动作
        if self.item_mode and self.pointer_mode == 'pointer':  # 添加item
            item = DiagramItem(self.item_mode, self.item_kwargs, event.scenePos(), self)
            self.addItem(item)
            self.parent().tool_box_button_group.checkedButton().setChecked(False) # 添加item后取消toolbox选定
            self.item_mode = None
            self.item_kwargs = None
        elif self.pointer_mode == 'line':  # 添加line
            self.line = QGraphicsLineItem(QLineF(event.scenePos(), event.scenePos()))
            # self.line.setPen(QPen(Qt.black, 2))
            self.addItem(self.line)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: PySide6.QtWidgets.QGraphicsSceneMouseEvent) -> None:
        # 移动item 或者 移动line 或者无动作
        if self.pointer_mode == 'line' and self.line: # 移动line
            line = QLineF(self.line.line().p1(), event.scenePos())
            self.line.setLine(line)
        elif self.pointer_mode == 'pointer' and self.item_mode == None:  # 移动item
            super(DiagramScene, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: PySide6.QtWidgets.QGraphicsSceneMouseEvent) -> None:
        # 如果当前正在连线则取消
        if self.line:
            # 获得line起点与终点的第一个不是line的item
            start_items = self.items(self.line.line().p1())
            while len(start_items) and start_items[0] == self.line:
                start_items.pop(0)
            
            end_items = self.items(self.line.line().p2())
            while len(end_items) and end_items[0] == self.line:
                end_items.pop(0)

            self.removeItem(self.line)
            self.line = None

            if (len(start_items) and len(end_items)) and (start_items[0] != end_items[0]):
                # arrow = Arrow(start_items[0], end_items[0])
                # self.addItem(arrow)
                print('arrow added')


        super().mouseReleaseEvent(event)
        

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle('AI Experiment Control System')

        # 初始化
        self.init_action()
        self.init_menu()
        self.init_view()
        self.init_toolbar()
        self.init_tool_box()
        self.init_property_box()
        self.init_layout()

    def init_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(self.tool_box)
        layout.addWidget(self.view)
        layout.addWidget(self.property_box)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def init_menu(self):
        # 创建菜单栏
        self.file_menu = self.menuBar().addMenu('File')
        self.file_menu.addAction(self.new_action)
        self.file_menu.addAction(self.open_action)
        self.file_menu.addAction(self.save_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)

        self.about_menu = self.menuBar().addMenu('About')
        self.about_menu.addAction(self.about_action)

    def init_toolbar(self):
        def pointer_clicked(i):
            self.scene.pointer_mode = self.toolbar_button_group.checkedButton().text()

        def scene_scale_changed(scale):
            # 视图大小改变
            new_scale = int(scale[:-1]) / 100.0
            old_matrix = self.view.transform()  # 获得当前的变换矩阵
            self.view.resetTransform()  # 重置变换矩阵为单位矩阵
            self.view.translate(old_matrix.dx(), old_matrix.dy())
            self.view.scale(new_scale, new_scale)

        # 创建工具栏
        edit_toolbar = self.addToolBar('Edit')
        edit_toolbar.addAction(self.new_action)
        edit_toolbar.addAction(self.open_action)
        edit_toolbar.addAction(self.save_action)
        edit_toolbar.addAction(self.delete_action)

        # 指针图标
        pointer_button = QToolButton()
        pointer_button.setText('pointer')
        pointer_button.setCheckable(True)
        pointer_button.setChecked(True)
        self.scene.pointer_mode = 'pointer'
        pointer_button.setIcon(QIcon(os.path.join('images', 'pointer.png')))

        # 连线图标
        line_button = QToolButton()
        line_button.setText('line')
        line_button.setCheckable(True)
        line_button.setIcon(QIcon(os.path.join('images', 'linepointer.png')))

        # 确保指针图标和连线图标只有一个能选中
        self.toolbar_button_group = QButtonGroup()
        self.toolbar_button_group.addButton(pointer_button, 0)
        self.toolbar_button_group.addButton(line_button, 1)
        self.toolbar_button_group.idClicked.connect(pointer_clicked)  # 当某个图标被选中

        # 缩放图标
        scene_scale_combo = QComboBox()
        scene_scale_combo.addItems(['50%', '75%', '100%', '125%', '150%'])
        scene_scale_combo.setCurrentIndex(2)
        scene_scale_combo.currentTextChanged.connect(scene_scale_changed)  # 更改缩放大小

        pointer_toolbar = self.addToolBar('Pointer type')
        pointer_toolbar.addWidget(pointer_button)
        pointer_toolbar.addWidget(line_button)
        pointer_toolbar.addWidget(scene_scale_combo)

        run_toolbar = self.addToolBar('Run')
        run_toolbar.addAction(self.run_action)

    def init_tool_box(self):
        # 创建工具箱（左栏）
        def button_group_clicked(i):
            # 只能不选或单选
            clicked_button = self.tool_box_button_group.button(i)
            for button in self.tool_box_button_group.buttons()[:]:
                if clicked_button != button:
                    button.setChecked(False)  # 取消其他按钮的选中，i按钮已经自动反选
            
            if clicked_button.isChecked():
                self.view.scene().item_mode = clicked_button.text()
                self.view.scene().item_kwargs = clicked_button.kwargs
            else:
                self.view.scene().item_mode = None
                self.view.scene().item_kwargs = None

        def create_cell_widget(text):
            button = QToolButton()
            button.setCheckable(True)
            button.setText(text)
            return button

        self.tool_box = QToolBox()
        self.tool_box.setToolTip('tool box')
        self.tool_box.setMinimumWidth(100)

        with open('modules2.json') as f:
            modules = json.load(f)

        self.tool_box_button_group = QButtonGroup()
        self.tool_box_button_group.setExclusive(False)  # 可以有任意多个选中
        self.tool_box_button_group.idClicked.connect(button_group_clicked)

        for k, v in modules['modules'].items():
            # 一个页面的button
            layout = QVBoxLayout()
            for js in v:
                button = create_cell_widget(js['func'])
                button.kwargs = js['kwargs']
                self.tool_box_button_group.addButton(button)
                layout.addWidget(button)
                pass  # 将属性添加至右边

            layout.addStretch()
            widget = QWidget()
            widget.setLayout(layout)
            self.tool_box.addItem(widget, k)

    def init_property_box(self):
        # 初始化属性栏
        layout = QFormLayout()
        layout.addRow(QLabel('test'))
        self.property_box = QWidget()
        self.property_box.setMinimumWidth(100)
        self.property_box.setLayout(layout)

    def init_view(self):
        # 初始化视图
        self.scene = DiagramScene(self)
        self.scene.setSceneRect(QRectF(0, 0, 5000, 5000))
        
        self.view = QGraphicsView(self.scene)

    def init_action(self):
        self.new_action = QAction('New', triggered=self.new)
        self.open_action = QAction('Open', triggered=self.open)
        self.save_action = QAction('Save', triggered=self.save)
        self.about_action = QAction('About', triggered=self.about)
        self.delete_action = QAction('Delete', triggered=self.delete)
        self.exit_action = QAction('Exit', triggered=self.exit)
        self.run_action = QAction('Run', triggered=self.run)

    def run(self):
        pass

    def new(self):
        pass

    def open(self):
        pass

    def save(self):
        pass

    def about(self):
        QMessageBox.about(self, 'About action', 'test message.')

    def delete(self):
        for item in self.scene.selectedItems():
            if isinstance(item, DiagramItem):
                # item.remove_arrows()
                print('请删除item关联的arrows')
            self.scene.removeItem(item)

    def exit(self):
        pass


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
    
