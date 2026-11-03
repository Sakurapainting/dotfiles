import QtQuick 2.0
import SddmComponents 2.0

Rectangle {
    id: root
    width: 1920
    height: 1080
    color: "#17171b"

    property color ink: "#17171b"
    property color panel: "#e61b1b20"
    property color line: "#506a6c85"
    property color accent: "#9294ae"
    property color accentBright: "#b1b2c6"
    property color muted: "#a3a2aa"
    property color textColor: "#f0eff2"
    property int sessionIndex: session.index
    property date clockTime: new Date()

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: root.clockTime = new Date()
    }

    TextConstants { id: textConstants }

    Connections {
        target: sddm
        function onLoginFailed() {
            password.text = ""
            status.text = textConstants.loginFailed
            password.forceActiveFocus()
        }
        function onLoginSucceeded() {
            status.text = textConstants.loginSucceeded
        }
        function onInformationMessage(message) {
            status.text = message
        }
    }

    Image {
        anchors.fill: parent
        source: Qt.resolvedUrl("background.jpg")
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        smooth: true
    }

    Rectangle {
        anchors.fill: parent
        color: "#6817171b"
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#3817171b" }
            GradientStop { position: 1.0; color: "#a617171b" }
        }
    }

    Column {
        anchors.centerIn: parent
        width: Math.min(420, parent.width - 40)
        spacing: 22

        Column {
            width: parent.width
            spacing: 7
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: Qt.formatTime(root.clockTime, "hh:mm")
                color: textColor
                font.family: "sans-serif"
                font.pixelSize: 58
                font.weight: Font.Light
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: Qt.formatDate(root.clockTime, Qt.DefaultLocaleLongDate)
                color: "#d0cfd4"
                font.family: "sans-serif"
                font.pixelSize: 15
            }
        }

        Rectangle {
            width: parent.width
            height: cardColumn.implicitHeight + 54
            radius: 22
            color: panel
            border.width: 1
            border.color: line

            Column {
                id: cardColumn
                anchors.centerIn: parent
                width: parent.width - 56
                spacing: 16

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "WELCOME BACK"
                    color: accentBright
                    font.family: "sans-serif"
                    font.pixelSize: 12
                    font.letterSpacing: 2.3
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: sddm.hostName
                    color: muted
                    font.family: "sans-serif"
                    font.pixelSize: 12
                    elide: Text.ElideRight
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                }

                Column {
                    width: parent.width
                    spacing: 7
                    Text { text: textConstants.userName; color: muted; font.pixelSize: 12 }
                    Rectangle {
                        width: parent.width
                        height: 44
                        radius: 9
                        color: "#86131317"
                        border.width: 1
                        border.color: username.activeFocus ? accent : "#3dffffff"
                        TextInput {
                            id: username
                            anchors.fill: parent
                            anchors.leftMargin: 13
                            anchors.rightMargin: 13
                            verticalAlignment: TextInput.AlignVCenter
                            text: userModel.lastUser
                            color: textColor
                            selectionColor: accent
                            selectedTextColor: ink
                            font.pixelSize: 15
                            clip: true
                            selectByMouse: true
                            KeyNavigation.tab: password
                            onAccepted: password.forceActiveFocus()
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: 7
                    Text { text: textConstants.password; color: muted; font.pixelSize: 12 }
                    Rectangle {
                        width: parent.width
                        height: 44
                        radius: 9
                        color: "#86131317"
                        border.width: 1
                        border.color: password.activeFocus ? accent : "#3dffffff"
                        TextInput {
                            id: password
                            anchors.fill: parent
                            anchors.leftMargin: 13
                            anchors.rightMargin: 13
                            verticalAlignment: TextInput.AlignVCenter
                            echoMode: TextInput.Password
                            color: textColor
                            selectionColor: accent
                            selectedTextColor: ink
                            font.pixelSize: 15
                            clip: true
                            selectByMouse: true
                            KeyNavigation.backtab: username
                            KeyNavigation.tab: session
                            onAccepted: doLogin()
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: 7
                    Text { text: textConstants.session; color: muted; font.pixelSize: 12 }
                    ComboBox {
                        id: session
                        width: parent.width
                        height: 40
                        model: sessionModel
                        index: sessionModel.lastIndex
                        color: "#86131317"
                        borderColor: "#3dffffff"
                        focusColor: accent
                        hoverColor: "#805f6078"
                        menuColor: "#f0212026"
                        textColor: textColor
                        arrowColor: accentBright
                        font.pixelSize: 14
                        rowDelegate: Component {
                            Text {
                                anchors.fill: parent
                                anchors.margins: 8
                                verticalAlignment: Text.AlignVCenter
                                color: textColor
                                font.pixelSize: 14
                                text: parent.modelItem.name
                            }
                        }
                        KeyNavigation.backtab: password
                        KeyNavigation.tab: loginButton
                    }
                }

                Text {
                    id: status
                    width: parent.width
                    height: 18
                    text: textConstants.prompt
                    color: muted
                    font.pixelSize: 12
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }

                Rectangle {
                    id: loginButton
                    width: parent.width
                    height: 46
                    radius: 10
                    color: loginMouse.containsMouse ? accentBright : accent
                    focus: true
                    KeyNavigation.backtab: session
                    KeyNavigation.tab: shutdownAction
                    Text {
                        anchors.centerIn: parent
                        text: textConstants.login
                        color: ink
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }
                    MouseArea {
                        id: loginMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: doLogin()
                    }
                    Keys.onReturnPressed: doLogin()
                    Keys.onEnterPressed: doLogin()
                }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 28
                    Text {
                        id: shutdownAction
                        text: textConstants.shutdown
                        color: shutdownMouse.containsMouse ? accentBright : muted
                        font.pixelSize: 12
                        focus: true
                        KeyNavigation.backtab: loginButton
                        KeyNavigation.tab: rebootAction
                        Keys.onReturnPressed: sddm.powerOff()
                        Keys.onEnterPressed: sddm.powerOff()
                        MouseArea { id: shutdownMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: sddm.powerOff() }
                    }
                    Text {
                        id: rebootAction
                        text: textConstants.reboot
                        color: rebootMouse.containsMouse ? accentBright : muted
                        font.pixelSize: 12
                        focus: true
                        KeyNavigation.backtab: shutdownAction
                        KeyNavigation.tab: username
                        Keys.onReturnPressed: sddm.reboot()
                        Keys.onEnterPressed: sddm.reboot()
                        MouseArea { id: rebootMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: sddm.reboot() }
                    }
                }
            }
        }
    }

    function doLogin() {
        sddm.login(username.text, password.text, session.index)
    }

    Component.onCompleted: {
        loginButton.activeFocusOnTab = true
        shutdownAction.activeFocusOnTab = true
        rebootAction.activeFocusOnTab = true
        if (username.text.length === 0)
            username.forceActiveFocus()
        else
            password.forceActiveFocus()
    }
}
