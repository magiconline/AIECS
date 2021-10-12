import sys
import math
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QGraphicsLineItem, QGraphicsItem, QGraphicsTextItem,
                               QGraphicsScene, QStyle, QHBoxLayout, QGraphicsView, QWidget, QButtonGroup,
                               QToolButton, QVBoxLayout, QToolBox, QComboBox, QMessageBox, QFormLayout, QLineEdit)
from PySide6.QtGui import QPolygonF, QPen, QIcon, QAction, QPainterPath
from PySide6.QtCore import Qt, QRectF, QSizeF, QLineF, QPointF, Signal
import PySide6
import os

class Arrow(QGraphicsLineItem):
    def __init__(self, start_item, end_item, parent=None, scene=None):
        super(Arrow, self).__init__(parent, scene)

        self.arrow_head = QPolygonF()
        self.arrow_size = 20.0  # 箭头大小
        self.start_item = start_item
        self.end_item = end_item
        self.color = Qt.black

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setPen(QPen(self.color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

    def boundingRect(self):
        # 由于箭头比直线大，重新计算graphics scene 需要刷新的范围
        extra = (self.pen().width() + self.arrow_size) / 2.0
        p1 = self.line().p1()
        p2 = self.line().p2()
        rect = QRectF(p1, QSizeF(p2.x() - p1.x(), p2.y() - p1.y()))
        return rect.normalized().adjusted(-extra, -extra, extra, extra)

    def shape(self):
        # 用于检查鼠标碰撞和选择
        path = super(Arrow, self).shape()
        path.addPolygon(self.arrow_head)
        return path

    def update_position(self):
        # 将 line 的 start 与 end 设置为连接的 item 的中心
        start = self.mapFromItem(self.start_item, 0, 0)
        end = self.mapFromItem(self.end_item, 0, 0)
        self.setLine(QLineF(start, end))

    def paint(self, painter, option, widget=None):
        if self.start_item.collidesWithItem(self.end_item):
            # 如果两个item碰撞就不绘制箭头
            return

        # pen用来绘制轮廓，brush用来填充
        painter.setPen(self.pen())
        painter.setBrush(self.color)

        # 遍历end item每条边与直线的交点，寻找箭头的位置
        center_line = QLineF(self.start_item.pos(), self.end_item.pos())
        end_polygon = self.end_item.polygon()
        p1 = end_polygon.at(0) + self.end_item.pos()
        intersect_point = QPointF()
        for i in end_polygon:
            p2 = i + self.end_item.pos()  # 相对坐标转换为绝对坐标
            poly_line = QLineF(p1, p2)
            intersectType, intersect_point = poly_line.intersects(center_line)
            if intersectType == QLineF.BoundedIntersection:
                break
            p1 = p2

        # 绘制直线
        self.setLine(QLineF(intersect_point, self.start_item.pos()))  # 线在图形下面，start item下多余的线被挡住

        # 绘制箭头
        line = self.line()
        angle = math.acos(line.dx() / line.length())
        if line.dy() >= 0:
            angle = (math.pi * 2.0) - angle
        arrow_head1 = QPointF(math.sin(angle + math.pi / 3.0) * self.arrow_size,
                              math.cos(angle + math.pi / 3) * self.arrow_size)
        arrow_p1 = line.p1() + arrow_head1  # 相对坐标转换为绝对坐标
        arrow_head2 = QPointF(math.sin(angle + math.pi - math.pi / 3.0) * self.arrow_size,
                              math.cos(angle + math.pi - math.pi / 3.0) * self.arrow_size)
        arrow_p2 = line.p1() + arrow_head2  # 相对坐标转换为绝对坐标
        self.arrow_head.clear()
        for point in [line.p1(), arrow_p1, arrow_p2]:
            self.arrow_head.append(point)
        painter.drawLine(line)
        painter.drawPolygon(self.arrow_head)

        # 如果被选中，显示虚线
        if self.isSelected():
            painter.setPen(QPen(self.color, 1, Qt.DashLine))
            my_line = QLineF(line)
            my_line.translate(0, 4.0)
            painter.drawLine(my_line)
            my_line.translate(0, -8.0)
            painter.drawLine(my_line)


class DiagramTextItem(QGraphicsTextItem):
    lost_focus = Signal(QGraphicsTextItem)
    selected_change = Signal(QGraphicsItem)

    def __init__(self, text='new widget', parent=None, scene=None, ):
        super(DiagramTextItem, self).__init__(parent, scene)

        # 默认不可移动、不可选择
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)

        # 设置类型
        # self.diagram_type = diagram_type

        # 设置初始文本
        self.setPlainText(text)

        # 连接的箭头列表
        self.arrows = []

        # 添加边框，添加polygon
        self._my_polygon = QPolygonF([
            QPointF(0, 0), QPointF(100, 0),
            QPointF(100, 100), QPointF(0, 100),
            QPointF(0, 0)])

    def polygon(self):
        return self._my_polygon

    def paint(self, painter: PySide6.QtGui.QPainter, option: PySide6.QtWidgets.QStyleOptionGraphicsItem,
              widget: PySide6.QtWidgets.QWidget) -> None:
        # 更改绘制样式，加上边框
        option.state |= QStyle.State_Selected
        super(DiagramTextItem, self).paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            # 如果被选中
            self.selected_change.emit(self)  # MainWindow更新文本
        elif change == QGraphicsItem.ItemPositionChange:
            for arrow in self.arrows:
                arrow.updatePosition()
        return value

    def focusOutEvent(self, event: PySide6.QtGui.QFocusEvent) -> None:
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.lost_focus.emit(self)  # 如果是空的则删除控件
        super(DiagramTextItem, self).focusOutEvent(event)

    def mouseDoubleClickEvent(self, event: PySide6.QtWidgets.QGraphicsSceneMouseEvent) -> None:
        # 双击可以编辑
        if self.textInteractionFlags() == Qt.NoTextInteraction:
            self.setTextInteractionFlags(Qt.TextEditorInteraction)
        super(DiagramTextItem, self).mouseDoubleClickEvent(event)

    def remove_arrow(self, arrow):
        self.arrows.remove(arrow)

    def remove_arrows(self):
        for arrow in self.arrows[:]:
            arrow.start_item().remove_arrow(arrow)
            arrow.end_item().remove_arrow(arrow)
            self.scene().removeItem(arrow)

    def add_arrow(self, arrow):
        self.arrows.append(arrow)


class DiagramScene(QGraphicsScene):
    InsertLine, InsertItem, MoveItem = range(3)
    item_inserted = Signal(DiagramTextItem)

    # item_selected = Signal(QGraphicsItem)

    def __init__(self, parent=None):
        super(DiagramScene, self).__init__(parent)

        self._my_mode = self.MoveItem
        self._my_item_type = None
        self.line = None
        self._text_item = None
        self._my_text_color = Qt.black
        self._my_line_color = Qt.black

    def set_mode(self, mode):
        self._my_mode = mode

    def set_item_type(self, type):
        self._my_item_type = type

    def editor_lost_focus(self, item):
        cursor = item.textCursor()
        cursor.clearSelection()
        item.setTextCursor(cursor)

        if not item.toPlainText():
            self.removeItem(item)
            item.deleteLater()

    def mousePressEvent(self, event: PySide6.QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if (event.button() != Qt.LeftButton):
            return

        if self._my_mode == self.InsertItem:
            item = DiagramTextItem()
            item.setTextInteractionFlags(Qt.TextEditorInteraction)
            item.setZValue(1000.0)
            item.lost_focus.connect(self.editor_lost_focus)
            # item.selected_change.connect(self.item_selected)
            self.addItem(item)
            item.setDefaultTextColor(self._my_text_color)
            item.setPos(event.scenePos())
            self.item_inserted.emit(item)

        elif self._my_mode == self.InsertLine:
            self.line = QGraphicsLineItem(QLineF(event.scenePos(), event.scenePos()))
            self.line.setPen(QPen(self._my_line_color, 2))
            self.addItem(self.line)

        super(DiagramScene, self).mousePressEvent(event)

    def mouseMoveEvent(self, event: PySide6.QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if (self._my_mode == self.InsertLine) and self.line:
            new_line = QLineF(self.line.line().p1(), event.scenePos())
            self.line.setLine(new_line)
        elif self._my_mode == self.MoveItem:
            super(DiagramScene, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: PySide6.QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if self.line and self._my_mode == self.InsertLine:
            start_items = self.items(self.line.line().p1())
            if len(start_items) and start_items[0] == self.line:
                start_items.pop(0)
            end_items = self.items(self.line.line().p2())
            if len(end_items) and end_items[0] == self.line:
                end_items.pop(0)

            self.removeItem(self.line)
            self.line = None

            if (len(start_items) and len(end_items) and
                    isinstance(start_items[0], DiagramTextItem) and
                    isinstance(end_items[0], DiagramTextItem) and
                    start_items[0] != end_items[0]):
                start_item = start_items[0]
                end_item = end_items[0]
                arrow = Arrow(start_item, end_item)
                start_item.add_arrow(arrow)
                end_item.add_arrow(arrow)
                arrow.setZValue(-1000.0)
                self.addItem(arrow)
                arrow.update_position()

        self.line = None
        super(DiagramScene, self).mouseReleaseEvent(event)

    def is_item_change(self, type):
        for item in self.selectedItems():
            if isinstance(item, type):
                return True
        return False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.create_actions()
        self.create_menus()
        self.create_tool_box()
        self.create_property()

        self.scene = DiagramScene()
        self.scene.setSceneRect(QRectF(0, 0, 5000, 5000))
        self.scene.item_inserted.connect(self.item_inserted)

        self.create_toolbars()

        layout = QHBoxLayout()
        layout.addWidget(self._tool_box)
        self.view = QGraphicsView(self.scene)
        layout.addWidget(self.view)
        layout.addWidget(self.property_widget)


        self.widget = QWidget()
        self.widget.setLayout(layout)

        self.setCentralWidget(self.widget)
        self.setWindowTitle("AIECS")

    def create_property(self):
        self.property_widget = QWidget()
        self.property_widget.setMinimumWidth(300)
        self.property_layout = QFormLayout()
        self.property_layout.addRow('属性1', QLineEdit())
        self.property_widget.setLayout(self.property_layout)

    def item_inserted(self, item):
        self._pointer_type_group.button(DiagramScene.MoveItem).setChecked(True)
        self.scene.set_mode(self._pointer_type_group.checkedId())
        self._button_group.button().setChecked(False)
        # self._button_group.button().setChecked(False)

    def create_actions(self):
        self._delete_action = QAction('Delete', self, triggered=self.delete_item)
        self._new_action = QAction('New', self, triggered=self.new)
        self._save_action = QAction('Save', self, triggered=self.save)
        self._open_action = QAction('Open', self, triggered=self.open)
        self._about_action = QAction('About', self, triggered=self.about)

    def new(self):
        pass

    def save(self):
        pass

    def open(self):
        pass

    def about(self):
        QMessageBox.about(self, 'About title', 'This is a test message.')

    def delete_item(self):
        for item in self.scene.selectedItems():
            if isinstance(item, DiagramTextItem):
                item.remove_arrows()
            self.scene.removeItem(item)

    def create_menus(self):
        self._file_menu = self.menuBar().addMenu('File')
        self._file_menu.addAction(self._new_action)
        self._file_menu.addAction(self._open_action)
        self._file_menu.addAction(self._save_action)
        self._file_menu.addAction(self._delete_action)

        self._about_menu = self.menuBar().addMenu('About')
        self._about_menu.addAction(self._about_action)

    def create_tool_box(self):
        self._button_group = QButtonGroup()  # 所有页面的button在一起，
        self._button_group.setExclusive(False)  # 可以不选中任何button
        self._button_group.idClicked.connect(self.button_group_clicked)  #

        layout = QVBoxLayout()
        layout.addWidget(self.create_cell_widget('input layer'))
        layout.addWidget(self.create_cell_widget('fcn layer'))
        layout.addStretch()

        item_widget = QWidget()
        item_widget.setLayout(layout)

        # self._background_button_group = QButtonGroup()
        # self._background_button_group.buttonClicked.connect(self.background_button_group_clicked)

        background_layout = QVBoxLayout()
        background_layout.addWidget(self.create_cell_widget('control 1'))
        background_layout.addWidget(self.create_cell_widget('control 2'))
        background_layout.addStretch()

        background_widget = QWidget()
        background_widget.setLayout(background_layout)

        self._tool_box = QToolBox()
        # self._tool_box.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Ignored))
        self._tool_box.setMinimumWidth(item_widget.sizeHint().width())
        self._tool_box.addItem(item_widget, 'layers')
        self._tool_box.addItem(background_widget, 'control')

    def button_group_clicked(self, idx):
        for button in self._button_group.buttons()[:]:
            if self._button_group.button(idx) != button:
                button.setChecked(False)

        self.scene.set_mode(DiagramScene.InsertItem)

    def create_cell_widget(self, text='new widget'):
        # 创建toolbox中的widget
        button = QToolButton()
        button.setText(text)
        button.setCheckable(True)
        self._button_group.addButton(button)

        return button

    def create_toolbars(self):
        self._edit_tool_bar = self.addToolBar('Edit')
        self._edit_tool_bar.addAction(self._new_action)
        self._edit_tool_bar.addAction(self._open_action)
        self._edit_tool_bar.addAction(self._save_action)
        self._edit_tool_bar.addAction(self._delete_action)

        pointer_button = QToolButton()
        pointer_button.setCheckable(True)
        pointer_button.setChecked(True)
        pointer_button.setIcon(QIcon('images/pointer.png'))

        line_pointer_button = QToolButton()
        line_pointer_button.setCheckable(True)
        line_pointer_button.setIcon(QIcon('images/linepointer.png'))

        self._pointer_type_group = QButtonGroup()
        self._pointer_type_group.addButton(pointer_button, DiagramScene.MoveItem)
        self._pointer_type_group.addButton(line_pointer_button, DiagramScene.InsertLine)
        self._pointer_type_group.idClicked.connect(self.pointer_group_clicked)

        self._scene_scale_combo = QComboBox()
        self._scene_scale_combo.addItems(['50%', '75%', '100%', '125%', '150%'])
        self._scene_scale_combo.setCurrentIndex(2)
        self._scene_scale_combo.currentTextChanged.connect(self.scene_scale_changed)

        self._pointer_toolbar = self.addToolBar('Pointer type')
        self._pointer_toolbar.addWidget(pointer_button)
        self._pointer_toolbar.addWidget(line_pointer_button)
        self._pointer_toolbar.addWidget(self._scene_scale_combo)

    def scene_scale_changed(self, scale):
        new_scale = int(scale[:-1]) / 100.0
        old_matrix = self.view.transform()
        self.view.resetTransform()
        self.view.translate(old_matrix.dx(), old_matrix.dy())
        self.view.scale(new_scale, new_scale)

    def pointer_group_clicked(self, i):
        self.scene.set_mode(self._pointer_type_group.checkedId())


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
