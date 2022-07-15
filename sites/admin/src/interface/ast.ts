/**
 * AST parsing and rendering.
 */

type NodeType = new(...args: any[]) => ASTNode

interface ASTObject {
    element: string
    children: Array<string|ASTObject>
}

/**
 * @class ASTNode
 */
class ASTNode {
    protected static NodeTypes: { [typename: string]: NodeType } = {}

    public children: ASTNode[] = []
    public typename: string
    private obj: any = {}

    public static registerNode(typename: string) {
        return (constructor: NodeType) => {
            ASTNode.NodeTypes[typename] = constructor
        }
    }

    public static loadNode(obj: ASTObject): ASTNode {
        const constructor: NodeType = ASTNode.NodeTypes[obj.element] || ASTNode
        const node = new constructor(obj)
        node.typename = (ASTNode.NodeTypes[obj.element] !== undefined) ? obj.element : "default_node"
        return node
    }

    constructor(obj: ASTObject) {
        this.obj = obj
    }
}

interface HeaderType extends ASTNode {
    sendChild(child: ASTNode): void
    get level(): number
}

function isHeader(node: any): node is HeaderType {
    return node.level !== undefined
}

class Stack<T> {
    private stack: T[] = []

    constructor(items?: T[]) {
        if (items) {
            this.stack = items
        }
    }

    public push(item: T) {
        this.stack.push(item)
    }

    public pop(): T {
        return this.stack.pop()
    }

    public get top(): T {
        return this.stack[this.stack.length - 1]
    }

    public isEmpty(): boolean {
        return this.stack.length === 0
    }
}

@ASTNode.registerNode("document")
export class DocumentNode extends ASTNode implements HeaderType {
    public preamble: ASTNode[] = []
    public children: HeaderType[]

    constructor(obj: { children: Array<ASTObject> } & ASTObject) {
        super(obj)

        const headers: Stack<HeaderType> = new Stack([this])
        obj.children.forEach((child: ASTObject) => {
            const node: ASTNode = ASTNode.loadNode(child)
            headers.top.sendChild(node)
            if(isHeader(node)) {
                if (node.level > headers.top.level) {
                    headers.push(node)
                } else {
                    while (node.level < headers.top.level) {
                        headers.pop()
                    }
                    headers.push(node)
                }
            }
        })
    }

    public sendChild(child: ASTNode): void {
        if (isHeader(child)) {
            this.children.push(child)
        } else {
            this.preamble.push(child)
        }
    }

    public get level(): number { return 0 }

    protected process_children(children: Array<string|ASTObject>): ASTNode[] {
        return children.map(ASTNode.loadNode) 
    }
}

@ASTNode.registerNode("heading")
export class HeadingNode extends ASTNode implements HeaderType {
    public readonly level: number
    public readonly label: ASTNode[]

    constructor(obj: { level: number, element: "heading" } & ASTObject) {
        super(obj)
        this.level = obj.level
        this.label = obj.children.map(ASTNode.loadNode)
    }

    public sendChild(child: ASTNode): void {
        this.children.push(child)
    }

}

@ASTNode.registerNode("directive_block")
export class DirectiveNode extends ASTNode {
    public readonly directiveType: string
    public readonly directive: string
    public readonly options: { [key: string]: string }

    constructor(obj: { directive_type: string, directive: string } & ASTObject) {
        super(obj)
        this.directiveType = obj.directive_type
        this.directive = obj.directive

        this.options = Object.fromEntries((this.children
            .filter(
                (child: ASTNode) => child instanceof DirectiveOptionNode
            ) as DirectiveOptionNode[])
            .map((optionNode: DirectiveOptionNode) => [optionNode.key, optionNode.value])
        )
            
    }
}

@ASTNode.registerNode("directive_option")
export class DirectiveOptionNode extends ASTNode {
    public readonly key: string
    public readonly value: string

    constructor(obj: {option: string, value: string} & ASTObject) {
        super(obj)
        this.key = obj.option
        this.value = obj.value
    }
}

class RecursiveNode extends ASTNode {
    public children: ASTNode[]

    constructor(obj: ASTObject) {
        super(obj)
        this.children = obj.children.map(ASTNode.loadNode)
    }
}

@ASTNode.registerNode("paragraph")
export class ParagraphNode extends RecursiveNode {
    constructor(obj: {} & ASTObject) {
        super(obj)
    }
}

@ASTNode.registerNode("raw_text")
export class TextNode extends ASTNode {
    public readonly text: string

    constructor(obj: { children: string } & ASTObject) {
        super(obj)
        this.text = obj.children
    }
}

@ASTNode.registerNode("blank_line")
export class BlankLineNode extends ASTNode {
    constructor(obj: {} & ASTObject) {
        super(obj)
    }
}

@ASTNode.registerNode("internal_link")
export class InternalLinkNode extends ASTNode {
    constructor(obj: {} & ASTObject) {
        super(obj)
    }
}

export default ASTNode