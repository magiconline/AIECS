import json
import os
import sys
from copy import deepcopy as copy
from typing import Any, Optional
from src.model import *

import PySide2
import numpy as np
from PySide2.QtCore import (QPointF, QRectF, QSizeF, Qt, QLineF, )
from PySide2.QtGui import (QIcon, QPen, QPolygonF, )
from PySide2.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox, QGraphicsItem, QGraphicsLineItem,
                               QGraphicsTextItem, QLineEdit, QMainWindow, QMessageBox, QSpinBox,
                               QToolBox, QHBoxLayout, QGraphicsView, QGraphicsScene, QWidget, QToolButton, QComboBox,
                               QFormLayout, QButtonGroup, QVBoxLayout, QLabel, QFileDialog, QAction)

# 功能
# TODO train, run, save/load model

# BUG
# TODO 测试新建、打开、保存、关闭功能 saved
# TODO 测试arrow, item 移动刷新

VERSION = "0.1.0"


class Arrow(QGraphicsLineItem):
    def __init__(self, start_item, end_item, parent=None, scene=None) -> None:
        super().__init__(parent, scene)
        self.start_item = start_item
        self.end_item = end_item

        self.arrow_size = 20.0
        self.arrow_head = QPolygonF()

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setPen(QPen(Qt.black, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

    def boundingRect(self) -> PySide2.QtCore.QRectF:
        # 由于箭头比直线大，重新计算graphics scene 需要刷新的范围
        extra = (self.pen().width() + self.arrow_size) / 2
        p1 = self.line().p1()
        p2 = self.line().p2()
        rect = QRectF(p1, QSizeF(p2.x() - p1.x(), p2.y() - p1.y()))
        return rect.normalized().adjusted(-extra, -extra, extra, extra)

    def shape(self) -> PySide2.QtGui.QPainterPath:
        # 用于检查鼠标碰撞和选择
        path = super().shape()
        path.addPolygon(self.arrow_head)
        return path

    def update_position(self):
        # 当start_item 与 end_item 移动时更新箭头
        start = self.mapFromItem(self.start_item, self.start_item.width() / 2, self.start_item.height() / 2)
        end = self.mapFromItem(self.end_item, self.end_item.width() / 2, self.end_item.height() / 2)
        self.setLine(QLineF(start, end))

    def paint(self, painter: PySide2.QtGui.QPainter, option: PySide2.QtWidgets.QStyleOptionGraphicsItem,
              widget: Optional[PySide2.QtWidgets.QWidget] = ...) -> None:
        # 绘制直线和箭头

        # pen 绘制轮廓，brush 填充
        painter.setPen(self.pen())
        painter.setBrush(Qt.black)

        if self.start_item.collidesWithItem(self.end_item):
            start_intersect_point = self.start_item.center_pos()
            end_intersect_point = self.end_item.center_pos()

        else:
            # 遍历 item.polygon 每条边与直线的交点，寻找箭头的位置
            center_line = QLineF(self.start_item.center_pos(), self.end_item.center_pos())
            end_polygon = self.end_item.polygon()
            p1 = end_polygon.at(0) + self.end_item.pos()
            end_intersect_point = QPointF()
            for i in end_polygon:
                p2 = i + self.end_item.pos()
                poly_line = QLineF(p1, p2)
                intersectType = poly_line.intersects(center_line, end_intersect_point)
                if intersectType == QLineF.BoundedIntersection:
                    break
                p1 = p2

            start_polygon = self.start_item.polygon()
            p1 = start_polygon.at(0) + self.start_item.pos()
            start_intersect_point = QPointF()
            for i in start_polygon:
                p2 = i + self.start_item.pos()
                poly_line = QLineF(p1, p2)
                intersectType = poly_line.intersects(center_line, start_intersect_point)
                if intersectType == QLineF.BoundedIntersection:
                    break
                p1 = p2

                # 绘制直线
        self.setLine(QLineF(end_intersect_point, start_intersect_point))

        # 绘制箭头
        if self.line().length() == 0:
            # 直线长度为0 不绘制箭头
            # print('length 0', time.time())
            return

        line = self.line()
        angle = np.arccos(line.dx() / line.length())
        if line.dy() >= 0:
            angle = (np.pi * 2.0) - angle
        arrow_head1 = QPointF(np.sin(angle + np.pi / 3.0) * self.arrow_size,
                              np.cos(angle + np.pi / 3) * self.arrow_size)
        arrow_p1 = line.p1() + arrow_head1  # 相对坐标转换为绝对坐标
        arrow_head2 = QPointF(np.sin(angle + np.pi - np.pi / 3.0) * self.arrow_size,
                              np.cos(angle + np.pi - np.pi / 3.0) * self.arrow_size)
        arrow_p2 = line.p1() + arrow_head2  # 相对坐标转换为绝对坐标
        self.arrow_head.clear()
        for point in [line.p1(), arrow_p1, arrow_p2]:
            self.arrow_head.append(point)
        painter.drawLine(line)
        painter.drawPolygon(self.arrow_head)

        # 如果被选中，显示虚线
        if self.isSelected():
            painter.setPen(QPen(Qt.black, 1, Qt.DashLine))
            my_line = QLineF(line)
            my_line.translate(0, 4.0)
            painter.drawLine(my_line)
            my_line.translate(0, -8.0)
            painter.drawLine(my_line)

    def remove_item_list(self):
        # 将自己从start_item 和 end_item 中的arrow list 删除
        self.start_item.out_arrows.remove(self)
        self.end_item.in_arrows.remove(self)


class DiagramItem(QGraphicsTextItem):

    def __init__(self, name, kwargs, pos, parent, dtype) -> None:
        # text:
        # kwargs:
        # dtype: model, data, preprocess, loss, optimizer, hyperparameters
        # id: 从0开始
        # pos
        # parent
        super(DiagramItem, self).__init__()

        self.dtype = dtype

        self.setPos(pos)
        self.setParent(parent)
        self.setFlag(QGraphicsItem.ItemIsMovable)  # 可以移动
        self.setFlag(QGraphicsItem.ItemIsSelectable)  # 可以选中

        self.setPlainText(name)
        self.kwargs = copy(kwargs)
        self.in_arrows = []
        self.out_arrows = []

    def center_pos(self) -> QPointF:
        # 返回item中心的绝对坐标
        top_left = self.pos()
        center = top_left + QPointF(self.width() / 2, self.height() / 2)
        return center

    def show_property(self) -> None:
        # 根据当前k与edit value生成槽函数
        def build_save(k: str, edit_value_func):
            def save():
                self.kwargs[k] = edit_value_func()

            return save
            # 清空布局

        self.clear_property()

        # 添加布局
        property_box: QWidget = self.parent().parent().property_box
        property_layout = property_box.layout()

        property_layout.addRow('name:5 ', QLabel(self.toPlainText()))
        property_layout.addRow('dtype: ', QLabel(self.dtype))

        for k, v in self.kwargs.items():
            if isinstance(v, bool):
                edit = QCheckBox()
                edit.setChecked(v)
                edit.clicked.connect(build_save(k, edit.isChecked))

            elif isinstance(v, int):
                edit = QSpinBox()
                edit.valueChanged.connect(build_save(k, edit.value))
                edit.setValue(v)

            elif isinstance(v, float):
                edit = QDoubleSpinBox()
                edit.valueChanged.connect(build_save(k, edit.value))
                edit.setValue(v)
                edit.setDecimals(5)

            elif isinstance(v, list):
                # TODO 支持列表
                pass
            else:
                edit = QLineEdit(v)
                edit.textChanged.connect(build_save(k, edit.text))

            property_layout.addRow(k, edit)

    def clear_property(self) -> None:
        # 清空布局
        property_layout = self.parent().parent().property_box.layout()
        while property_layout.rowCount() > 0:
            property_layout.removeRow(0)

    def itemChange(self, change: PySide2.QtWidgets.QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.ItemPositionChange:
            # item 被移动
            for arrow in self.in_arrows:
                arrow.updatePosition()
            for arrow in self.out_arrows:
                arrow.updatePosition()
            self.parent().parent().saved = False

        elif change == QGraphicsItem.ItemSelectedChange:
            # item 选中状态改变
            if self.isSelected():
                self.clear_property()  # 取消选中后清除

                # 取消编辑后文本选择状态清除
                cursor = self.textCursor()
                cursor.clearSelection()
                self.setTextCursor(cursor)

                # 失去焦点时不可修改text
                self.setTextInteractionFlags(Qt.NoTextInteraction)

            else:
                self.show_property()

        return super().itemChange(change, value)

    def remove_arrow(self, arrow: Arrow) -> None:
        arrow.remove_item_list()  # 将箭头从所连接的item list 中删除
        self.parent().removeItem(arrow)  # 将箭头从scene中删除

    def remove_arrows(self) -> None:
        for arrow in self.in_arrows[:]:
            self.remove_arrow(arrow)

        for arrow in self.out_arrows[:]:
            self.remove_arrow(arrow)

    def polygon(self) -> QPolygonF:
        rect = self.boundingRect()
        # top_left = rect.topLeft()
        polygon = QPolygonF(rect)
        return polygon

    def width(self) -> float:
        return self.boundingRect().width()

    def height(self) -> float:
        return self.boundingRect().height()


class DiagramScene(QGraphicsScene):
    def __init__(self, parent):
        super().__init__()
        self.item_text = None  # 'str' , None
        self.item_kwargs = None  # model, data, preprocess, loss, optimizer, hyperparameters or None
        self.dtype = None
        self.pointer_mode = None  # 'pointer', 'line'
        self.line = None
        self.setParent(parent)
        self.item_count = 0

    def mousePressEvent(self, event: PySide2.QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if event.button() != Qt.LeftButton:  # 只响应左键
            return

        # 摁下左键：添加item 或 临时显示line 或 无动作
        if self.item_text and self.pointer_mode == 'pointer':
            # 添加item
            item = DiagramItem(self.item_text + '_' + str(self.item_count), self.item_kwargs, event.scenePos(), self, self.dtype)
            self.addItem(item)
            self.item_count += 1

            self.parent().saved = False
            # 添加item后, toolbox中的item取消选定
            # self.parent().tool_box_button_group.checkedButton().setChecked(False)
            # self.item_text = None
            # self.dtype = None
            # self.item_kwargs = None

        elif self.pointer_mode == 'line':
            # 添加line
            self.line = QGraphicsLineItem(QLineF(event.scenePos(), event.scenePos()))
            self.line.setPen(QPen(Qt.black, 2))
            self.addItem(self.line)

            self.parent().saved = False

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: PySide2.QtWidgets.QGraphicsSceneMouseEvent) -> None:
        # 移动item 或者 移动line 或者无动作
        if self.pointer_mode == 'line' and self.line:  # 移动line
            line = QLineF(self.line.line().p1(), event.scenePos())
            self.line.setLine(line)
            self.parent().saved = False
        elif self.pointer_mode == 'pointer':
            super(DiagramScene, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: PySide2.QtWidgets.QGraphicsSceneMouseEvent) -> None:
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

            if (len(start_items) and len(end_items)) and (
                    start_items[0] != end_items[0] and (not self.items_connected(start_items[0], end_items[0]))):
                # 两个item存在 且 不相同 且 未连线
                arrow = Arrow(start_items[0], end_items[0])
                start_items[0].out_arrows.append(arrow)
                end_items[0].in_arrows.append(arrow)
                self.addItem(arrow)
                arrow.update_position()

                self.parent().saved = False

        super().mouseReleaseEvent(event)

    def items_connected(self, item1: DiagramItem, item2: DiagramItem) -> bool:
        # 判断两个item是否连线
        # item1 <- item2: 查找item1 in_arrows list 与 item2 out_arrows list 中是否有相同的arrow
        for arrow1 in item1.in_arrows:
            if arrow1 in item2.out_arrows:
                return True

        # item1 -> item2: 查找item1 out_arrows list 与 item2 in_arrows list 中是否有相同的arrow
        for arrow2 in item2.in_arrows:
            if arrow2 in item1.out_arrows:
                return True

        return False


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle('AI Experiment Control System')

        self.module_path = 'modules.json'
        self.save_file_path = None
        self.save_version = "0.1.0"
        self.saved = True

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
                self.view.scene().item_text = clicked_button.text()
                self.view.scene().dtype = clicked_button.dtype
                self.view.scene().item_kwargs = clicked_button.kwargs
            else:
                self.view.scene().item_text = None
                self.view.scene().dtype = None
                self.view.scene().item_kwargs = None

        def create_cell_widget(text):
            button = QToolButton()
            button.setCheckable(True)
            button.setText(text)
            return button

        self.tool_box = QToolBox()
        self.tool_box.setMinimumWidth(150)

        with open(self.module_path) as f:
            modules = json.load(f)
        self.module_version = modules['version']

        self.tool_box_button_group = QButtonGroup()
        self.tool_box_button_group.setExclusive(False)  # 可以有任意多个选中
        self.tool_box_button_group.idClicked.connect(button_group_clicked)

        for k, v in modules['modules'].items():
            # 一个页面的button
            layout = QVBoxLayout()
            for js in v:
                button = create_cell_widget(js['name'])
                button.kwargs = js['kwargs']
                button.dtype = k
                self.tool_box_button_group.addButton(button)
                layout.addWidget(button)

            layout.addStretch()
            widget = QWidget()
            widget.setLayout(layout)
            self.tool_box.addItem(widget, k)

    def init_property_box(self):
        # 初始化属性栏
        layout = QFormLayout()
        self.property_box = QWidget()
        self.property_box.setMinimumWidth(250)
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
        if not self.save():
            print('运行失败')
            return False

        with open(self.save_file_path) as f:
            js_file = json.load(f)

        # 检测版本
        if js_file['save_version'] != self.save_version:
            print('Warning! Different save version.')

        if js_file['module_version'] != self.module_version:
            print('Warning! Different module version.')

        f = None
        for model in js_file['models']:
            if model['dtype'] == 'hyperparameters':
                if not f:
                    f = eval(model['kwargs']['func'])
                else:
                    print('Error! More than one hyperparameter model.')
                    return False

        if f is None:
            print('Error! No hyperparameter model.')

        f(js_file['models'])

        print('运行成功')
        return True

    def new(self):
        if self.close():
            self.save_file_path = None
            self.saved = True
            print("新建成功")

        else:
            print("新建失败")

    def open(self):
        def add_item(model):
            item = DiagramItem(model['name'], model['kwargs'], QPointF(*model['pos']), self.scene, model['dtype'])    
            self.scene.addItem(item)

            for item_kwargs in model['in_items']:
                in_item = add_item(item_kwargs)
                
                arrow = Arrow(in_item, item)
                in_item.out_arrows.append(arrow)
                item.in_arrows.append(arrow)
                self.scene.addItem(arrow)
                arrow.update_position()

            return item
        # 选择文件
        file_name = QFileDialog.getOpenFileName(self, 'open file', '.')[0]
        
        if file_name == '':
            print('打开失败')
            return False

        if self.saved or self.close():
            # 读取文件
            with open(file_name) as f:
                models = json.load(f)

            if models['save_version'] != self.save_version:
                print('Warning! Different save version.')

            if models['module_version'] != self.module_version:
                print('Warning! Different module version.')

            self.scene.item_count = models['scene']['item_count']

            # 创建item, arrow
            for model in models['models']:
                add_item(model)

            self.save_file_path = file_name
            self.saved = True
            print('打开成功')
            return True

        else:
            print('打开失败')
            return False

    def save(self):
        def traverse(item: DiagramItem) -> dict:
            # 保存自己
            ret = {
                'name': item.toPlainText(),
                'dtype': item.dtype,
                'pos': [item.pos().x(), item.pos().y()],
                'kwargs': item.kwargs,
                'in_items': [traverse(arrow.start_item) for arrow in item.in_arrows],
            }
            return ret

        js = {}
        js['save_version'] = self.save_version
        js['module_version'] = self.module_version

        # 保存scene
        scene = self.scene
        js['scene'] = {}
        js['scene']['item_count'] = scene.item_count

        # 保存item
        js['models'] = []

        for item in scene.items():
            if isinstance(item, DiagramItem) and len(item.out_arrows) == 0:
                # 找到队尾item
                js['models'].append(traverse(item))

        # 保存
        # 检查self.save_file_path，如果为None则提示输入文件名
        if self.save_file_path == None:
            save_file_path = QFileDialog.getOpenFileName(self, 'Choose save file', '.')[0]
            
            if save_file_path != '':
                self.save_file_path = save_file_path
            else:
                print('保存失败')
                return False

        with open(self.save_file_path, 'w') as f:
            json.dump(js, f)

        print('File saved in', self.save_file_path)

        self.saved = True
        print('保存成功')
        return True

    def about(self):
        QMessageBox.about(self, 'About action', 'test message.')

    def delete(self):
        for item in self.scene.selectedItems():
            if isinstance(item, DiagramItem):
                # 删除item前删除所连接的所有箭头
                item.remove_arrows()
            elif isinstance(item, Arrow):
                # 删除箭头前将自己从所连接的item中删除
                item.remove_item_list()
            else:
                print('删除错误：', type(item))

            self.scene.removeItem(item)

        self.saved = False

    def exit(self):
        if self.close() == True:
            sys.exit(0)

    def close(self):
        # 检测是否保存，如果未保存则提示保存
        if not self.saved:
            choice = QMessageBox.warning(self, 'Close without saving!', 'Do you want to close without saving?',
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

            if choice == QMessageBox.No:
                if not self.save():
                    # 保存失败
                    print('关闭失败')
                    return False

            elif choice == QMessageBox.Cancel:
                print('关闭失败')
                return False

        self.init_view()

        self.scene.pointer_mode = self.toolbar_button_group.checkedButton().text()
        checked_button = self.tool_box_button_group.checkedButton()
        if checked_button:
            checked_button.setChecked(False)

        self.init_layout()

        print('关闭成功')
        return True

if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
