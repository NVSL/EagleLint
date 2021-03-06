import collections

Point = collections.namedtuple("Point", "x y")


# Given three colinear points p, q, r, the function checks if
# point q lies on line segment 'pr'
def onSegment(p, q, r):
    if q.x <= max(p.x, r.x) and q.x >= min(p.x, r.x) and \
                    q.y <= max(p.y, r.y) and q.y >= min(p.y, r.y):
        return True

    return False


# To find orientation of ordered triplet (p, q, r).
# The function returns following values
# 0 --> p, q and r are colinear
# 1 --> Clockwise
# 2 --> Counterclockwise
def orientation(p, q, r):
    # See https:#www.geeksforgeeks.org/orientation-3-ordered-points/
    # for details of below formula.
    val = (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y)

    if val == 0:
        return 0  # colinear

    return 1 if (val > 0) else 2  # clock or counterclock wise


# The main function that returns true if line segment 'p1q1'
# and 'p2q2' intersect.
def doIntersect(p1, q1, p2, q2):
    # Find the four orientations needed for general and
    # special cases
    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)

    # General case
    if o1 != o2 and o3 != o4:
        return True

    # Special Cases
    # p1, q1 and p2 are colinear and p2 lies on segment p1q1
    if o1 == 0 and onSegment(p1, p2, q1):
        return True

    # p1, q1 and p2 are colinear and q2 lies on segment p1q1
    if o2 == 0 and onSegment(p1, q2, q1):
        return True

    # p2, q2 and p1 are colinear and p1 lies on segment p2q2
    if o3 == 0 and onSegment(p2, p1, q2):
        return True

    # p2, q2 and q1 are colinear and q1 lies on segment p2q2
    if o4 == 0 and onSegment(p2, q1, q2):
        return True

    return False


# Driver program to test above functions
def main():
    p1 = Point(1, 1);
    q1 = Point(10, 1)
    p2 = Point(1, 2);
    q2 = Point(10, 2)

    print doIntersect(p1, q1, p2, q2)

    p1 = Point(10, 0);
    q1 = Point(0, 10)
    p2 = Point(0, 0);
    q2 = Point(10, 10)
    print doIntersect(p1, q1, p2, q2)

    p1 = Point(-5, -5);
    q1 = Point(0, 0)
    p2 = Point(1, 1);
    q2 = Point(10, 10)
    print doIntersect(p1, q1, p2, q2)


if __name__ == "__main__":
    main()
